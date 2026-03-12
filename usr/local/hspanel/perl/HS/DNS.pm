package HS::DNS;

use strict;
use warnings;
use JSON;
use File::Path qw(make_path);

my $DNS_DB     = "/var/hspanel/conf/dns_zones.json";
my $ZONES_DIR  = "/var/hspanel/dns";
my $WRAP_SYSOP = "/usr/local/hspanel/bin/wrap_sysop";

sub _load_db {
    my $db = {};
    if (-f $DNS_DB) {
        open(my $fh, '<', $DNS_DB) or return {};
        my $json = do { local $/; <$fh> };
        close($fh);
        $db = decode_json($json) if $json;
    }
    return $db;
}

sub _save_db {
    my ($db) = @_;
    my $dir = $DNS_DB;
    $dir =~ s|/[^/]+$||;
    make_path($dir) unless -d $dir;
    open(my $fh, '>', $DNS_DB) or return 0;
    print $fh to_json($db, { pretty => 1 });
    close($fh);
    return 1;
}

sub _write_zone_file {
    my ($domain, $zone) = @_;
    make_path($ZONES_DIR) unless -d $ZONES_DIR;
    my $zone_file = "$ZONES_DIR/$domain.zone";

    my $serial = $zone->{serial} || _serial();
    my $records = $zone->{records} || [];

    open(my $fh, '>', $zone_file) or return (0, "Unable to write zone file");
    print $fh "\$TTL 300\n";
    print $fh "@ IN SOA ns1.$domain. hostmaster.$domain. ( $serial 3600 900 1209600 300 )\n";
    print $fh "@ IN NS ns1.$domain.\n";
    print $fh "@ IN NS ns2.$domain.\n";

    for my $r (@$records) {
        my $name = $r->{name} || '@';
        my $type = $r->{type} || 'A';
        my $ttl  = $r->{ttl}  || 300;
        my $val  = $r->{value} || '';
        next unless $val;
        print $fh "$name $ttl IN $type $val\n";
    }

    close($fh);
    return (1, $zone_file);
}

sub _serial {
    my @t = gmtime(time);
    return sprintf("%04d%02d%02d01", $t[5] + 1900, $t[4] + 1, $t[3]);
}

sub _reload_dns {
    my $rc = system($WRAP_SYSOP, 'reload_pdns');
    return $rc == 0;
}

sub rebuild_zone {
    my ($class, %args) = @_;
    
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $ip     = $args{ip}     || "127.0.0.1";
    
    my $db = _load_db();
    $db->{zones} ||= {};

    my $zone = $db->{zones}{$domain} || {
        serial  => _serial(),
        records => [],
        status  => 'active',
    };

    # Ensure baseline records exist.
    my @defaults = (
        { name => '@',    type => 'A',     value => $ip, ttl => 300 },
        { name => 'www',  type => 'CNAME', value => $domain . '.', ttl => 300 },
        { name => 'mail', type => 'A',     value => $ip, ttl => 300 },
        { name => '@',    type => 'MX',    value => '10 mail.' . $domain . '.', ttl => 300 },
    );

    my @records = @{$zone->{records}};
    for my $d (@defaults) {
        my $exists = 0;
        for my $r (@records) {
            if (($r->{name} || '') eq $d->{name} && ($r->{type} || '') eq $d->{type} && ($r->{value} || '') eq $d->{value}) {
                $exists = 1;
                last;
            }
        }
        push @records, $d unless $exists;
    }

    $zone->{records} = \@records;
    $zone->{serial} = _serial();
    $db->{zones}{$domain} = $zone;

    my ($ok, $zone_file) = _write_zone_file($domain, $zone);
    return { success => 0, error => $zone_file } unless $ok;

    _save_db($db);
    _reload_dns();

    return {
        success   => 1,
        message   => "Zone file compiled successfully.",
        zone_file => $zone_file,
        serial    => $zone->{serial},
    };
}

sub list_zones {
    my ($class, %args) = @_;
    my $db = _load_db();
    my @zones;
    for my $domain (sort keys %{ $db->{zones} || {} }) {
        my $z = $db->{zones}{$domain};
        push @zones, {
            domain  => $domain,
            records => scalar @{ $z->{records} || [] },
            serial  => $z->{serial} || _serial(),
            status  => $z->{status} || 'active',
        };
    }
    return { success => 1, zones => \@zones, total => scalar @zones };
}

sub add_record {
    my ($class, %args) = @_;
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $type   = $args{type}   || return { success => 0, error => "Missing record type" };
    my $name   = $args{name}   || '@';
    my $value  = $args{value}  || return { success => 0, error => "Missing value" };
    my $ttl    = $args{ttl}    || 14400;

    my $db = _load_db();
    $db->{zones} ||= {};
    $db->{zones}{$domain} ||= { serial => _serial(), records => [], status => 'active' };

    push @{ $db->{zones}{$domain}{records} }, {
        id    => time . int(rand(10000)),
        name  => $name,
        type  => uc($type),
        value => $value,
        ttl   => int($ttl),
    };
    $db->{zones}{$domain}{serial} = _serial();

    my ($ok, $zone_file) = _write_zone_file($domain, $db->{zones}{$domain});
    return { success => 0, error => $zone_file } unless $ok;

    _save_db($db);
    _reload_dns();

    return {
        success => 1,
        message => "DNS record added: $name $type $value (TTL: $ttl) for $domain",
    };
}

sub delete_record {
    my ($class, %args) = @_;
    my $domain    = $args{domain}    || return { success => 0, error => "Missing domain" };
    my $record_id = $args{record_id} || return { success => 0, error => "Missing record_id" };

    my $db = _load_db();
    return { success => 0, error => "Zone not found" }
        unless exists $db->{zones}{$domain};

    my @kept;
    my $removed = 0;
    for my $r (@{ $db->{zones}{$domain}{records} || [] }) {
        if (($r->{id} || '') eq $record_id || ($record_id eq 'all')) {
            $removed++;
            next;
        }
        push @kept, $r;
    }
    $db->{zones}{$domain}{records} = \@kept;
    $db->{zones}{$domain}{serial} = _serial();

    my ($ok, $zone_file) = _write_zone_file($domain, $db->{zones}{$domain});
    return { success => 0, error => $zone_file } unless $ok;

    _save_db($db);
    _reload_dns();
    return { success => 1, message => "Record $record_id deleted from $domain zone.", removed => $removed };
}

sub edit_record {
    my ($class, %args) = @_;
    my $domain    = $args{domain}    || return { success => 0, error => "Missing domain" };
    my $record_id = $args{record_id} || return { success => 0, error => "Missing record_id" };

    my $type  = $args{type};
    my $value = $args{value};
    my $ttl   = $args{ttl};

    my $db = _load_db();
    return { success => 0, error => "Zone not found" }
        unless exists $db->{zones}{$domain};

    my $updated = 0;
    for my $r (@{ $db->{zones}{$domain}{records} || [] }) {
        next unless (($r->{id} || '') eq $record_id);
        $r->{type} = uc($type) if $type;
        $r->{value} = $value if defined $value;
        $r->{ttl} = int($ttl) if defined $ttl;
        $updated = 1;
        last;
    }

    return { success => 0, error => "Record not found" } unless $updated;

    $db->{zones}{$domain}{serial} = _serial();
    my ($ok, $zone_file) = _write_zone_file($domain, $db->{zones}{$domain});
    return { success => 0, error => $zone_file } unless $ok;

    _save_db($db);
    _reload_dns();

    return { success => 1, message => "Record $record_id updated in $domain zone." };
}

1;

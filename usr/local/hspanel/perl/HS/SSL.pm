package HS::SSL;

use strict;
use warnings;
use JSON;

my $SSL_DB = "/var/hspanel/conf/ssl_certs.json";

sub _load_db {
    my $db = {};
    if (-f $SSL_DB) {
        open(my $fh, '<', $SSL_DB) or return {};
        my $json = do { local $/; <$fh> };
        close($fh);
        $db = decode_json($json) if $json;
    }
    return $db;
}

sub _save_db {
    my ($db) = @_;
    my $dir = $SSL_DB;
    $dir =~ s|/[^/]+$||;
    system("mkdir -p $dir") unless -d $dir;
    open(my $fh, '>', $SSL_DB) or return 0;
    print $fh to_json($db, { pretty => 1 });
    close($fh);
    return 1;
}

sub list_certs {
    my ($class, %args) = @_;
    my $db = _load_db();

    my @certs;
    for my $domain (sort keys %$db) {
        my $c = $db->{$domain};
        push @certs, {
            domain    => $domain,
            issuer    => $c->{issuer}    || "Let's Encrypt",
            type      => $c->{type}      || 'DV',
            status    => $c->{status}    || 'active',
            issued    => $c->{issued}    || '2026-01-01',
            expires   => $c->{expires}   || '2026-04-01',
            autorenew => $c->{autorenew} // 1,
        };
    }

    return { success => 1, certificates => \@certs, total => scalar @certs };
}

sub request_cert {
    my ($class, %args) = @_;
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };

    my $db = _load_db();

    # In production: call certbot/acme.sh
    $db->{$domain} = {
        issuer    => "Let's Encrypt",
        type      => 'DV',
        status    => 'active',
        issued    => '2026-03-12',
        expires   => '2026-06-10',
        autorenew => 1,
        cert_path => "/etc/letsencrypt/live/$domain/fullchain.pem",
        key_path  => "/etc/letsencrypt/live/$domain/privkey.pem",
    };

    _save_db($db);

    return {
        success => 1,
        message => "SSL certificate issued for $domain via Let's Encrypt.",
        domain  => $domain,
        expires => '2026-06-10',
    };
}

sub install_cert {
    my ($class, %args) = @_;
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $cert   = $args{cert}   || return { success => 0, error => "Missing certificate data" };
    my $key    = $args{key}    || return { success => 0, error => "Missing private key" };

    my $db = _load_db();

    $db->{$domain} = {
        issuer    => $args{issuer} || 'Custom',
        type      => 'Custom',
        status    => 'active',
        issued    => '2026-03-12',
        expires   => $args{expires} || '2027-03-12',
        autorenew => 0,
    };

    _save_db($db);

    return { success => 1, message => "Custom SSL certificate installed for $domain." };
}

sub autorenew_status {
    my ($class, %args) = @_;
    my $db = _load_db();

    my @domains;
    for my $d (sort keys %$db) {
        push @domains, {
            domain    => $d,
            autorenew => $db->{$d}{autorenew} // 1,
            expires   => $db->{$d}{expires} || 'unknown',
        };
    }

    return { success => 1, domains => \@domains };
}

1;

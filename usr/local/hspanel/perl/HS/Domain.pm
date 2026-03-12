package HS::Domain;

use strict;
use warnings;
use JSON;
use File::Path qw(make_path);

require HS::Web;
require HS::DNS;
require HS::SSL;

my $REGISTRY = "/var/hspanel/userdata/domains.json";

sub _load_registry {
    return {} unless -f $REGISTRY;
    open(my $fh, '<', $REGISTRY) or return {};
    my $raw = do { local $/; <$fh> };
    close($fh);
    return {} unless $raw;
    my $data = eval { decode_json($raw) };
    return $data || {};
}

sub _save_registry {
    my ($data) = @_;
    my $dir = $REGISTRY;
    $dir =~ s|/[^/]+$||;
    make_path($dir) unless -d $dir;

    open(my $fh, '>', $REGISTRY) or return 0;
    print $fh to_json($data, { pretty => 1 });
    close($fh);
    return 1;
}

sub create {
    my ($class, %args) = @_;

    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $user   = $args{user}   || 'hspanel';
    my $php    = $args{php}    || '8.2';
    my $ip     = $args{ip}     || '127.0.0.1';

    return { success => 0, error => "Invalid domain" }
        unless $domain =~ /^(?!-)[A-Za-z0-9\-]{1,63}(?:\.[A-Za-z0-9\-]{1,63})+$/;

    my $registry = _load_registry();
    return { success => 0, error => "Domain already exists" }
        if exists $registry->{$domain};

    my $docroot = "/home/$user/public_html";
    my $web = HS::Web->create_vhost(domain => $domain, user => $user, docroot => $docroot, php => $php);
    return $web unless $web->{success};

    my $dns = HS::DNS->rebuild_zone(domain => $domain, ip => $ip);

    my $ssl = HS::SSL->issue(domain => $domain);

    $registry->{$domain} = {
        domain      => $domain,
        owner       => $user,
        docroot     => $docroot,
        php         => $php,
        ip          => $ip,
        dns_enabled => $dns->{success} ? JSON::true : JSON::false,
        ssl_enabled => $ssl->{success} ? JSON::true : JSON::false,
        created_at  => time,
        status      => 'active',
    };

    _save_registry($registry) or return { success => 0, error => "Failed to write domain registry" };

    return {
        success => 1,
        message => "Domain provisioned: $domain",
        domain  => $domain,
        web     => $web,
        dns     => $dns,
        ssl     => $ssl,
    };
}

sub list {
    my ($class, %args) = @_;
    my $owner = $args{owner};

    my $registry = _load_registry();
    my @domains;

    for my $name (sort keys %$registry) {
        my $entry = $registry->{$name};
        next if $owner && ($entry->{owner} || '') ne $owner;
        push @domains, $entry;
    }

    return {
        success => 1,
        domains => \@domains,
        total   => scalar @domains,
    };
}

sub delete {
    my ($class, %args) = @_;

    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };

    my $registry = _load_registry();
    return { success => 0, error => "Domain not found" }
        unless exists $registry->{$domain};

    my $web = HS::Web->delete_vhost(domain => $domain);
    my $dns = HS::DNS->delete_record(domain => $domain, record_id => 'all');

    delete $registry->{$domain};
    _save_registry($registry) or return { success => 0, error => "Failed to update domain registry" };

    return {
        success => 1,
        message => "Domain removed: $domain",
        web     => $web,
        dns     => $dns,
    };
}

sub set_php {
    my ($class, %args) = @_;

    my $domain  = $args{domain}  || return { success => 0, error => "Missing domain" };
    my $version = $args{version} || return { success => 0, error => "Missing version" };

    my $registry = _load_registry();
    return { success => 0, error => "Domain not found" }
        unless exists $registry->{$domain};

    my $result = HS::Web->set_php_version(domain => $domain, version => $version);
    return $result unless $result->{success};

    $registry->{$domain}{php} = $version;
    _save_registry($registry);

    return {
        success => 1,
        message => "PHP version updated for $domain",
        domain  => $domain,
        version => $version,
    };
}

1;

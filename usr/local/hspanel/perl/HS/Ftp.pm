package HS::Ftp;

use strict;
use warnings;
use JSON;
use File::Path qw(make_path);

my $FTP_DB = "/var/hspanel/conf/ftp_accounts.json";
my $WRAP_SYSOP = "/usr/local/hspanel/bin/wrap_sysop";

sub _load_db {
    my $db = {};
    if (-f $FTP_DB) {
        open(my $fh, '<', $FTP_DB) or return {};
        my $json = do { local $/; <$fh> };
        close($fh);
        $db = decode_json($json) if $json;
    }
    return $db;
}

sub _save_db {
    my ($db) = @_;
    my $dir = $FTP_DB;
    $dir =~ s|/[^/]+$||;
    make_path($dir) unless -d $dir;

    open(my $fh, '>', $FTP_DB) or return 0;
    print $fh to_json($db, { pretty => 1 });
    close($fh);
    return 1;
}

sub create {
    my ($class, %args) = @_;

    my $username = $args{username} || $args{user} || return { success => 0, error => "Missing username" };
    my $password = $args{password} || return { success => 0, error => "Missing password" };
    my $domain   = $args{domain}   || '';
    my $path     = $args{path}     || '/public_html';

    return { success => 0, error => "Invalid username" }
        unless $username =~ /^[a-z0-9._-]{1,64}$/;

    my $db = _load_db();
    $db->{accounts} ||= {};
    return { success => 0, error => "FTP account already exists" }
        if exists $db->{accounts}{$username};

    my $home = $path;
    if ($domain && $path eq '/public_html') {
        $home = "/home/$username/public_html/$domain";
    }

    my $res = system($WRAP_SYSOP, 'ftp_create_user', $username, $password, $home);

    $db->{accounts}{$username} = {
        username  => $username,
        domain    => $domain,
        home      => $home,
        status    => ($res == 0 ? 'active' : 'pending'),
        created   => scalar localtime(),
    };
    _save_db($db);

    if ($res != 0) {
        return {
            success => 0,
            error   => 'Failed to create FTP account at system level',
            account => $db->{accounts}{$username},
        };
    }

    return {
        success => 1,
        message => "FTP account '$username' created.",
        account => $db->{accounts}{$username},
    };
}

sub list {
    my ($class, %args) = @_;
    my $db = _load_db();
    my @accounts = map { $db->{accounts}{$_} } sort keys %{ $db->{accounts} || {} };
    return { success => 1, accounts => \@accounts, total => scalar @accounts };
}

1;

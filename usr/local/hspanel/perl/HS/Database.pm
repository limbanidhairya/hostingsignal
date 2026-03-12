package HS::Database;

use strict;
use warnings;
use JSON;

my $DB_REGISTRY = "/var/hspanel/conf/databases.json";
my $MYSQL_SOCKET = "/var/run/mysqld/mysqld.sock";

sub _load_db {
    my $db = {};
    if (-f $DB_REGISTRY) {
        open(my $fh, '<', $DB_REGISTRY) or return {};
        my $json = do { local $/; <$fh> };
        close($fh);
        $db = decode_json($json) if $json;
    }
    return $db;
}

sub _save_db {
    my ($db) = @_;
    my $dir = $DB_REGISTRY;
    $dir =~ s|/[^/]+$||;
    system("mkdir -p $dir") unless -d $dir;
    open(my $fh, '>', $DB_REGISTRY) or return 0;
    print $fh to_json($db, { pretty => 1 });
    close($fh);
    return 1;
}

sub list_databases {
    my ($class, %args) = @_;
    my $owner = $args{owner};

    my ($rc, $out, $err) = _run_mysql('SHOW DATABASES;');
    if ($rc != 0) {
        return { success => 0, error => "Failed to list databases: $err" };
    }

    my $reg = _load_db();
    my @system = qw(mysql information_schema performance_schema sys hspanel);
    my %skip = map { $_ => 1 } @system;
    my @databases;

    for my $line (split(/\n/, $out)) {
        my $name = $line;
        $name =~ s/^\s+|\s+$//g;
        next if !$name || $name eq 'Database' || $skip{$name};

        my $meta = $reg->{databases}{$name} || {};
        next if $owner && ($meta->{owner} || '') ne $owner;

        push @databases, {
            name    => $name,
            owner   => $meta->{owner} || 'unknown',
            engine  => 'MariaDB',
            size_mb => $meta->{size_mb} || 0,
            tables  => $meta->{tables} || 0,
            created => $meta->{created} || 'unknown',
        };
    }

    return { success => 1, databases => \@databases, total => scalar @databases };
}

sub create {
    my ($class, %args) = @_;
    my $name  = $args{name}  || return { success => 0, error => "Missing database name" };
    my $owner = $args{owner} || 'root';

    return { success => 0, error => "Invalid database name. Use 3-32 alphanumeric/underscore." }
        unless $name =~ /^[a-zA-Z0-9_]{3,32}$/;

    my ($rc, $out, $err) = _run_mysql("CREATE DATABASE IF NOT EXISTS `$name` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;");
    return { success => 0, error => "Failed to create database: $err" } if $rc != 0;

    my $reg = _load_db();
    $reg->{databases} ||= {};
    $reg->{databases}{$name} = {
        owner   => $owner,
        engine  => 'MariaDB',
        size_mb => 0,
        tables  => 0,
        created => scalar localtime(),
    };
    _save_db($reg);

    return { success => 1, message => "Database '$name' created.", database => $name };
}

sub delete {
    my ($class, %args) = @_;
    my $name = $args{name} || return { success => 0, error => "Missing database name" };

    return { success => 0, error => "Cannot delete protected database" }
        if $name =~ /^(mysql|information_schema|performance_schema|sys|hspanel)$/;

    my ($rc, $out, $err) = _run_mysql("DROP DATABASE IF EXISTS `$name`;");
    return { success => 0, error => "Failed to drop database: $err" } if $rc != 0;

    my $reg = _load_db();
    $reg->{databases} ||= {};
    delete $reg->{databases}{$name};
    _save_db($reg);

    return { success => 1, message => "Database '$name' dropped." };
}

sub list_users {
    my ($class, %args) = @_;

    my ($rc, $out, $err) = _run_mysql("SELECT User, Host FROM mysql.user ORDER BY User;");
    return { success => 0, error => "Failed to list users: $err" } if $rc != 0;

    my @users;
    for my $line (split(/\n/, $out)) {
        next if $line =~ /^User\s+/;
        my ($user, $host) = split(/\s+/, $line, 2);
        next if !$user;
        next if $user =~ /^(mysql|root|mariadb\.sys|debian-sys-maint)$/;
        push @users, {
            username  => $user,
            host      => ($host || 'localhost'),
            databases => [],
        };
    }

    return { success => 1, users => \@users, total => scalar @users };
}

sub create_user {
    my ($class, %args) = @_;
    my $username = $args{username} || return { success => 0, error => "Missing username" };
    my $password = $args{password} || return { success => 0, error => "Missing password" };
    my $database = $args{database};

    return { success => 0, error => "Invalid username" }
        unless $username =~ /^[a-zA-Z0-9_]{1,64}$/;

    my $escaped = $password;
    $escaped =~ s/\\/\\\\/g;
    $escaped =~ s/'/\\'/g;

    my ($rc, $out, $err) = _run_mysql("CREATE USER IF NOT EXISTS '$username'\@'localhost' IDENTIFIED BY '$escaped';");
    return { success => 0, error => "Failed to create DB user: $err" } if $rc != 0;

    if ($database) {
        return { success => 0, error => "Invalid database name" }
            unless $database =~ /^[a-zA-Z0-9_]{1,64}$/;
        my ($grc, $gout, $gerr) = _run_mysql("GRANT ALL PRIVILEGES ON `$database`.* TO '$username'\@'localhost'; FLUSH PRIVILEGES;");
        return { success => 0, error => "Failed to grant DB privileges: $gerr" } if $grc != 0;
    }

    my $reg = _load_db();
    $reg->{users} ||= {};
    $reg->{users}{$username} = {
        databases => $database ? [$database] : [],
        host      => 'localhost',
        created   => scalar localtime(),
    };
    _save_db($reg);

    return { success => 1, message => "Database user '$username' created.", username => $username };
}

sub _run_mysql {
    my ($sql) = @_;
    my $cmd = "mysql --socket $MYSQL_SOCKET -u root -e \"$sql\" 2>&1";
    my $out = `$cmd`;
    my $rc = $? >> 8;
    return ($rc, $out, $out);
}

1;

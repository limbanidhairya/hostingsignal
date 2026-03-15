package HS::Cron;

use strict;
use warnings;
use JSON;

my $CRON_DB = "/var/hspanel/conf/cron_jobs.json";

sub _load_db {
    my $db = {};
    if (-f $CRON_DB) {
        open(my $fh, '<', $CRON_DB) or return {};
        my $json = do { local $/; <$fh> };
        close($fh);
        $db = decode_json($json) if $json;
    }
    return $db;
}

sub _save_db {
    my ($db) = @_;
    my $dir = $CRON_DB;
    $dir =~ s|/[^/]+$||;
    system("mkdir -p $dir") unless -d $dir;
    open(my $fh, '>', $CRON_DB) or return 0;
    print $fh to_json($db, { pretty => 1 });
    close($fh);
    return 1;
}

sub list_jobs {
    my ($class, %args) = @_;
    my $user = $args{user};
    my $db = _load_db();

    my @jobs;
    for my $id (sort keys %$db) {
        next if $user && $db->{$id}{user} ne $user;
        push @jobs, {
            id      => $id,
            minute  => $db->{$id}{minute}  || '*',
            hour    => $db->{$id}{hour}    || '*',
            day     => $db->{$id}{day}     || '*',
            month   => $db->{$id}{month}   || '*',
            weekday => $db->{$id}{weekday} || '*',
            command => $db->{$id}{command} || '',
            user    => $db->{$id}{user}    || 'root',
            status  => $db->{$id}{status}  || 'active',
        };
    }

    return { success => 1, jobs => \@jobs, total => scalar @jobs };
}

sub add {
    my ($class, %args) = @_;
    return $class->create(%args);
}

sub create {
    my ($class, %args) = @_;
    my $command = $args{command} || return { success => 0, error => "Missing command" };

    my $id = "cron_" . time() . "_" . int(rand(9999));

    my $db = _load_db();
    $db->{$id} = {
        minute  => $args{minute}  || '*/5',
        hour    => $args{hour}    || '*',
        day     => $args{day}     || '*',
        month   => $args{month}   || '*',
        weekday => $args{weekday} || '*',
        command => $command,
        user    => $args{user}    || 'root',
        status  => 'active',
        created => '2026-03-12',
    };

    _save_db($db);

    return { success => 1, message => "Cron job created.", id => $id };
}

sub delete {
    my ($class, %args) = @_;
    my $id = $args{id} || return { success => 0, error => "Missing id" };

    my $db = _load_db();
    return { success => 0, error => "Job not found" }
        unless exists $db->{$id};

    delete $db->{$id};
    _save_db($db);

    return { success => 1, message => "Cron job $id deleted." };
}

sub update {
    my ($class, %args) = @_;
    my $id = $args{id} || return { success => 0, error => "Missing id" };

    my $db = _load_db();
    return { success => 0, error => "Job not found" }
        unless exists $db->{$id};

    for my $field (qw(minute hour day month weekday command status)) {
        $db->{$id}{$field} = $args{$field} if defined $args{$field};
    }

    _save_db($db);

    return { success => 1, message => "Cron job $id updated." };
}

1;

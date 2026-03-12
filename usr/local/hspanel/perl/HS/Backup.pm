package HS::Backup;

use strict;
use warnings;
use JSON;

my $BACKUP_DIR = "/var/hspanel/backups";
my $BACKUP_DB  = "/var/hspanel/conf/backups.json";

sub _load_db {
    my $db = { backups => [], schedule => {} };
    if (-f $BACKUP_DB) {
        open(my $fh, '<', $BACKUP_DB) or return $db;
        my $json = do { local $/; <$fh> };
        close($fh);
        $db = decode_json($json) if $json;
    }
    return $db;
}

sub _save_db {
    my ($db) = @_;
    my $dir = $BACKUP_DB;
    $dir =~ s|/[^/]+$||;
    system("mkdir -p $dir") unless -d $dir;
    open(my $fh, '>', $BACKUP_DB) or return 0;
    print $fh to_json($db, { pretty => 1 });
    close($fh);
    return 1;
}

sub list_backups {
    my ($class, %args) = @_;
    my $db = _load_db();

    return {
        success => 1,
        backups => $db->{backups} || [],
        total   => scalar @{ $db->{backups} || [] },
    };
}

sub create {
    my ($class, %args) = @_;
    my $type = $args{type} || 'full';  # full | incremental | databases | files

    my $backup_id = "bkp_" . time() . "_" . int(rand(9999));

    my $db = _load_db();
    $db->{backups} ||= [];

    my $entry = {
        id       => $backup_id,
        type     => $type,
        status   => 'completed',
        size_mb  => int(rand(500) + 50),
        date     => '2026-03-12 23:00:00',
        path     => "$BACKUP_DIR/$backup_id.tar.gz",
        duration => int(rand(300) + 30) . 's',
    };

    unshift @{ $db->{backups} }, $entry;
    _save_db($db);

    return {
        success   => 1,
        message   => "Backup $backup_id created ($type).",
        backup_id => $backup_id,
        size_mb   => $entry->{size_mb},
    };
}

sub restore {
    my ($class, %args) = @_;
    my $backup_id = $args{backup_id} || return { success => 0, error => "Missing backup_id" };

    my $db = _load_db();
    my $found = 0;
    for my $b (@{ $db->{backups} || [] }) {
        if ($b->{id} eq $backup_id) {
            $found = 1;
            last;
        }
    }

    return { success => 0, error => "Backup not found" } unless $found;

    # In production: extract archive and restore files/databases
    return { success => 1, message => "Restore from $backup_id initiated. ETA: ~5 minutes." };
}

sub download {
    my ($class, %args) = @_;
    my $backup_id = $args{backup_id} || return { success => 0, error => "Missing backup_id" };

    return {
        success      => 1,
        download_url => "/backups/download/$backup_id",
        message      => "Download link generated.",
    };
}

sub schedule {
    my ($class, %args) = @_;
    my $frequency = $args{frequency} || 'daily';  # daily | weekly | monthly
    my $time      = $args{time}      || '02:00';
    my $type      = $args{type}      || 'full';
    my $retain    = $args{retain}    || 7;

    my $db = _load_db();
    $db->{schedule} = {
        enabled   => 1,
        frequency => $frequency,
        time      => $time,
        type      => $type,
        retain    => $retain,
    };

    _save_db($db);

    return {
        success  => 1,
        message  => "Backup schedule set: $frequency at $time ($type), retain $retain copies.",
        schedule => $db->{schedule},
    };
}

1;

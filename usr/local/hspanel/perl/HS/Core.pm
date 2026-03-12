package HS::Core;

use strict;
use warnings;

sub ping {
    my ($class, %args) = @_;
    return {
        success => 1,
        message => 'pong',
        ts      => time,
    };
}

sub version {
    my ($class, %args) = @_;
    my $version_file = '/usr/local/hspanel/VERSION';
    my $version = 'unknown';

    if (-f $version_file) {
        open(my $fh, '<', $version_file);
        my $v = <$fh>;
        close($fh);
        $v =~ s/\s+$// if defined $v;
        $version = $v if $v;
    }

    return {
        success => 1,
        version => $version,
    };
}

sub health {
    my ($class, %args) = @_;

    my @checks = (
        { name => 'queue_dir', path => '/var/hspanel/queue', ok => (-d '/var/hspanel/queue' ? 1 : 0) },
        { name => 'users_dir', path => '/var/hspanel/users', ok => (-d '/var/hspanel/users' ? 1 : 0) },
        { name => 'wrap_sysop', path => '/usr/local/hspanel/bin/wrap_sysop', ok => (-x '/usr/local/hspanel/bin/wrap_sysop' ? 1 : 0) },
        { name => 'config', path => '/usr/local/hspanel/config/hspanel.conf', ok => (-f '/usr/local/hspanel/config/hspanel.conf' ? 1 : 0) },
    );

    my $ok = 1;
    for my $c (@checks) {
        $ok = 0 unless $c->{ok};
    }

    return {
        success => ($ok ? 1 : 0),
        status  => ($ok ? 'healthy' : 'degraded'),
        checks  => \@checks,
        ts      => time,
    };
}

sub status {
    my ($class, %args) = @_;
    return health($class, %args);
}

1;

package HS::Metrics;

use strict;
use warnings;
use JSON;

sub system_info {
    my ($class, %args) = @_;

    if ($^O eq 'linux') {
        my $hostname = `hostname 2>/dev/null` || 'hs-server';
        chomp $hostname;
        my $os = `cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'"' -f2` || 'Linux';
        chomp $os;
        my $kernel = `uname -r 2>/dev/null` || 'unknown';
        chomp $kernel;
        my $uptime = `uptime -p 2>/dev/null` || 'unknown';
        chomp $uptime;

        return {
            success  => 1,
            hostname => $hostname,
            os       => $os,
            kernel   => $kernel,
            uptime   => $uptime,
            arch     => 'x86_64',
        };
    }

    # Mock data for Windows dev
    return {
        success  => 1,
        hostname => 'hs-dev-server',
        os       => 'Ubuntu 24.04.1 LTS',
        kernel   => '6.8.0-45-generic',
        uptime   => 'up 14 days, 6 hours, 32 minutes',
        arch     => 'x86_64',
    };
}

sub cpu_ram_disk {
    my ($class, %args) = @_;

    if ($^O eq 'linux') {
        # Real metrics on Linux
        my $cpu_line = `top -bn1 | grep 'Cpu(s)' 2>/dev/null` || '';
        my $cpu = 0;
        if ($cpu_line =~ /(\d+\.\d+)\s*id/) {
            $cpu = sprintf("%.1f", 100 - $1);
        }

        my @mem = split(/\s+/, `free -m | grep Mem 2>/dev/null` || '');
        my $ram_total = $mem[1] || 1;
        my $ram_used  = $mem[2] || 0;

        my @disk = split(/\s+/, `df -BM / | tail -1 2>/dev/null` || '');
        my $disk_total = $disk[1] || '1M';
        my $disk_used  = $disk[2] || '0M';

        $disk_total =~ s/M//;
        $disk_used  =~ s/M//;

        return {
            success    => 1,
            cpu_pct    => $cpu + 0,
            ram_total  => $ram_total + 0,
            ram_used   => $ram_used + 0,
            ram_pct    => sprintf("%.1f", ($ram_used / ($ram_total || 1)) * 100) + 0,
            disk_total => int($disk_total / 1024),
            disk_used  => int($disk_used / 1024),
            disk_pct   => sprintf("%.1f", ($disk_used / ($disk_total || 1)) * 100) + 0,
        };
    }

    # Mock data
    return {
        success    => 1,
        cpu_pct    => 23.5,
        cpu_cores  => 8,
        ram_total  => 16384,
        ram_used   => 6841,
        ram_pct    => 41.8,
        disk_total => 250,
        disk_used  => 87,
        disk_pct   => 34.8,
    };
}

sub bandwidth {
    my ($class, %args) = @_;

    return {
        success   => 1,
        today_gb  => 12.4,
        month_gb  => 342.8,
        limit_gb  => 1000,
        month_pct => 34.3,
    };
}

sub processes {
    my ($class, %args) = @_;

    if ($^O eq 'linux') {
        my @lines = `ps aux --sort=-%cpu | head -11 2>/dev/null`;
        shift @lines;  # remove header

        my @procs;
        for my $line (@lines) {
            my @f = split(/\s+/, $line, 11);
            push @procs, {
                user    => $f[0],
                pid     => $f[1],
                cpu_pct => $f[2] + 0,
                mem_pct => $f[3] + 0,
                command => $f[10] || '',
            };
        }

        return { success => 1, processes => \@procs };
    }

    # Mock data
    return {
        success   => 1,
        processes => [
            { user => 'www-data', pid => 1234,  cpu_pct => 12.3, mem_pct => 4.2, command => 'apache2' },
            { user => 'mysql',    pid => 2345,  cpu_pct => 8.7,  mem_pct => 15.1, command => 'mysqld' },
            { user => 'nobody',   pid => 3456,  cpu_pct => 5.2,  mem_pct => 2.8, command => 'php-fpm: pool www' },
            { user => 'root',     pid => 4567,  cpu_pct => 3.1,  mem_pct => 1.5, command => 'named' },
            { user => 'vmail',    pid => 5678,  cpu_pct => 1.8,  mem_pct => 3.2, command => 'dovecot' },
            { user => 'postfix',  pid => 6789,  cpu_pct => 0.9,  mem_pct => 1.1, command => 'master' },
            { user => 'root',     pid => 7890,  cpu_pct => 0.5,  mem_pct => 0.8, command => 'sshd' },
            { user => 'root',     pid => 8901,  cpu_pct => 0.3,  mem_pct => 0.4, command => 'cron' },
        ],
    };
}

1;

package Whostmgr::UserConfig;

use strict;
use warnings;
use Fcntl qw(:flock);
use File::Path qw(make_path);

=head1 NAME

Whostmgr::UserConfig - Parse and modify /var/cpanel/users/$user flat files.

=head1 DESCRIPTION

In typical cPanel architecture, the `/var/cpanel/users/` directory contains 
flat text files mapping user variables like STARTDATE, RS, IP, DNS, etc.
This module provides a parser and writer for that format.

=cut

our $USER_DATA_DIR = "cpanel_files/var/cpanel/users";

sub load_user {
    my ($class, $user) = @_;
    
    return { success => 0, error => "Missing user" } unless $user;
    
    my $filepath = "$USER_DATA_DIR/$user";
    unless (-e $filepath) {
        return { success => 0, error => "User config $user does not exist.", path => $filepath };
    }
    
    my %config;
    open(my $fh, '<', $filepath) or return { success => 0, error => "Cannot open $filepath: $!" };
    while (<$fh>) {
        chomp;
        # Format is typically KEY=VALUE
        if (/^([A-Za-z0-9_]+)=(.*)$/) {
            $config{$1} = $2;
        }
    }
    close($fh);
    
    return { success => 1, data => \%config };
}

sub save_user {
    my ($class, $user, $data_hashref) = @_;
    return { success => 0, error => "Missing user" } unless $user;
    
    make_path($USER_DATA_DIR) unless -d $USER_DATA_DIR;
    
    my $filepath = "$USER_DATA_DIR/$user";
    
    open(my $fh, '>', $filepath) or return { success => 0, error => "Cannot write to $filepath: $!" };
    flock($fh, LOCK_EX);
    
    foreach my $key (sort keys %$data_hashref) {
        my $val = $data_hashref->{$key};
        print $fh "$key=$val\n";
    }
    
    flock($fh, LOCK_UN);
    close($fh);
    
    return { success => 1, message => "User config $user saved." };
}

1; # End of module

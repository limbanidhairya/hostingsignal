package Whostmgr::Packages;

use strict;
use warnings;

=head1 NAME

Whostmgr::Packages - Shared Hosting Package Management

=head1 DESCRIPTION

Reads and writes package files used to define quotas and features
for new accounts. In native cPanel, this is in /var/cpanel/packages.

=cut

sub create_package {
    my ($class, %args) = @_;
    
    my $name = $args{name} || return { success => 0, error => "Package name missing" };
    
    my $pkg_data = {
        QUOTA => $args{quota} || 'unlimited',
        BWLIMIT => $args{bwlimit} || 'unlimited',
        MAXFTP => $args{maxftp} || 'unlimited',
        MAXSQL => $args{maxsql} || 'unlimited',
        MAXPOP => $args{maxpop} || 'unlimited',
        MAXSUB => $args{maxsub} || 'unlimited',
        MAXPARK => $args{maxpark} || 'unlimited',
        MAXADDON => $args{maxaddon} || 'unlimited',
        FEATURELIST => $args{featurelist} || 'default',
        CGIAccess => $args{cgi} || 'n',
    };
    
    my $file_content = "";
    foreach my $k (keys %$pkg_data) {
        $file_content .= "$k=$pkg_data->{$k}\n";
    }
    
    # In full system, this writes to /var/cpanel/packages/$name
    print "Creating package: $name\n---\n$file_content---\n";
    
    return { success => 1, message => "Package $name created" };
}

sub get_package {
    my ($class, $name) = @_;
    
    # Mocking standard default package response
    if ($name eq 'default') {
        return {
            success => 1,
            data => {
                QUOTA => 1000,
                BWLIMIT => 10000,
                MAXFTP => 'unlimited',
                MAXSQL => 'unlimited',
                MAXPOP => 'unlimited'
            }
        };
    }
    
    return { success => 0, error => "Package not found." };
}

1; # End of module

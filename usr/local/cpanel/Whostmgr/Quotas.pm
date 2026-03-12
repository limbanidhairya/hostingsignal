package Whostmgr::Quotas;

use strict;
use warnings;

=head1 NAME

Whostmgr::Quotas - Disk and Bandwidth Quota Management

=head1 DESCRIPTION

Module that interfaces with OS-level `edquota` and bandwidth logging.

=cut

sub set_disk_quota {
    my ($class, $user, $quota_megabytes) = @_;
    
    return { success => 0, error => "Missing user" } unless $user;
    $quota_megabytes ||= 0; # 0 is unlimited usually
    
    # Mocking `setquota` which cPanel uses underneath.
    # setquota -u $user $quota_megabytes $quota_megabytes 0 0 -a
    
    my $cmd = "setquota -u $user $quota_megabytes $quota_megabytes 0 0 -a";
    print "Executing Quota Command: $cmd\n";
    
    return { success => 1, message => "Quota set to $quota_megabytes MB for $user" };
}

sub get_disk_usage {
    my ($class, $user) = @_;
    
    # Mocking `repquota`
    # repquota -u $user
    
    return {
        success => 1,
        data => {
            user => $user,
            used => 250, # MB
            limit => 1000 # MB
        }
    };
}

1; # End of module

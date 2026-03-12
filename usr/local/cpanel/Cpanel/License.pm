package Cpanel::License;

use strict;
use warnings;
use JSON;

=head1 NAME

Cpanel::License - Mock License Module for HostingSignal

=head1 DESCRIPTION

This module replaces the proprietary RSA license check found in standard cPanel.
Since HostingSignal is open source and doesn't require store.cpanel.net callbacks,
this returns a perpetually valid license object.

=cut

sub check_license {
    my $class = shift;
    
    my $license_status = {
        'status'  => 'active',
        'type'    => 'HostingSignal Free',
        'ip'      => '127.0.0.1',
        'company' => 'Internal Development',
        'valid'   => 1
    };
    
    return $license_status;
}

sub get_license_key {
    my $class = shift;
    return 'HS-FREE-FOREVER-XXX';
}

sub is_expired {
    my $class = shift;
    # Never expired
    return 0;
}

1; # End of module

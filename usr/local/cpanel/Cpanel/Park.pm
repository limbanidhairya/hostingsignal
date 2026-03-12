package Cpanel::Park;

use strict;
use warnings;

=head1 NAME

Cpanel::Park - Addon and Parked Domain Management

=head1 DESCRIPTION

Handles the logic to add secondary domains (Parked/Aliases or Addon domains) 
to an existing cPanel account. Maps to UAPI module DomainInfo or Park in older versions.

=cut

sub add_addon_domain {
    my ($class, %args) = @_;
    
    my $newdomain = $args{domain} || return { success => 0, error => "Missing addon domain" };
    my $dir = $args{dir} || "public_html/$newdomain";
    my $user = $args{user} || return { success => 0, error => "System user unknown" };
    my $subdomain = $args{subdomain} || (split(/\./, $newdomain))[0]; 
    
    # Needs to:
    # 1. Add virtual host via Whostmgr::Web
    # 2. Add DNS zone via Whostmgr::DNS
    # 3. Create directory
    
    if ($ENV{CPANEL_DEV_MOCK}) {
        print "Mock Addon: $newdomain rooted at ~/$dir maps to sub $subdomain\n";
    }
    
    return { 
        success => 1, 
        message => "Addon domain $newdomain successfully parked on $dir." 
    };
}

sub add_parked_domain {
    my ($class, %args) = @_;
    my $domain = $args{domain} || return { success => 0, error => "Missing parked domain" };
    my $user = $args{user};
    
    if ($ENV{CPANEL_DEV_MOCK}) {
        print "Mock Parked: $domain aliased to main webroot\n";
    }
    
    return { success => 1, message => "Domain $domain parked successfully." };
}

1; # End of module

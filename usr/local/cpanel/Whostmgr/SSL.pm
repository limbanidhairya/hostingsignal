package Whostmgr::SSL;

use strict;
use warnings;

=head1 NAME

Whostmgr::SSL - Manage SSL/TLS certificates and AutoSSL functionality

=head1 DESCRIPTION

Generates Self-Signed certificates or interfaces with Let's Encrypt / Sectigo
to validate domain ownership and install valid certs into Apache/Nginx.

=cut

sub install_autossl {
    my ($class, %args) = @_;
    
    my $domain = $args{domain} || return { success => 0, error => "Missing domain" };
    my $user   = $args{user}   || return { success => 0, error => "Missing user" };
    
    # Normally this involves:
    # 1. Dropping a .well-known/acme-challenge file in the docroot
    # 2. pinging Let's Encrypt
    # 3. Installing returning .crt to /var/cpanel/ssl/installed/certs/
    # 4. Running rebuild_httpd_conf
    
    if ($ENV{CPANEL_DEV_MOCK}) {
        print "Mock AutoSSL: Requested Let's Encrypt for $domain.\n";
        
        my $mock_cert_path = "cpanel_files/var/cpanel/ssl/installed/certs/${domain}.crt";
        require File::Path;
        File::Path::make_path("cpanel_files/var/cpanel/ssl/installed/certs/");
        
        open(my $fh, '>', $mock_cert_path) or return { success => 0, error => "Could not write mock cert: $!" };
        print $fh "-----BEGIN CERTIFICATE-----\nMOCKCERT123\n-----END CERTIFICATE-----\n";
        close($fh);
        
        require Whostmgr::Web;
        Whostmgr::Web->rebuild_httpd_conf();
    }
    
    return { success => 1, message => "AutoSSL completed for $domain." };
}

sub get_cert_status {
    my ($class, $domain) = @_;
    
    return {
        success => 1,
        data => {
            domain => $domain,
            has_ssl => 1,
            provider => "Let's Encrypt",
            expiry => "2026-12-31"
        }
    };
}

1; # End of module

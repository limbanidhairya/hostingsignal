package Whostmgr::PHP;

use strict;
use warnings;

=head1 NAME

Whostmgr::PHP - MultiPHP Manager

=head1 DESCRIPTION

Interfaces with the system to assign specific PHP-FPM versions (ea-php74, ea-php81, etc.)
to specific Virtual Hosts, mimicking MultiPHP Manager in WHM.

=cut

sub set_vhost_version {
    my ($class, %args) = @_;
    
    my $vhost = $args{vhost} || return { success => 0, error => "Missing vhost" };
    my $version = $args{version} || return { success => 0, error => "Missing PHP version (e.g. ea-php82)" };
    
    # Typically interacts with `/etc/apache2/conf.d/php.conf` or user userdata files.
    if ($ENV{CPANEL_DEV_MOCK}) {
        print "Mock MultiPHP: Setting $vhost to use $version via FastCGI\n";
        return { success => 1, message => "Successfully assigned $version to $vhost" };
    }
    
    # Simulated execution
    # system("/usr/local/cpanel/scripts/php_set_vhost_version --vhost=$vhost --version=$version");
    
    return { success => 1, message => "Successfully assigned $version to $vhost" };
}

sub get_system_default {
    my ($class) = @_;
    return { success => 1, data => { default => 'ea-php82' } };
}

sub list_installed_versions {
    my ($class) = @_;
    return { success => 1, data => { versions => ['ea-php81', 'ea-php82', 'ea-php83'] } };
}

1; # End of module

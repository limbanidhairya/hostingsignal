package CpanelAPI;

use strict;
use warnings;
use JSON;

=head1 NAME

CpanelAPI - API Dispatcher for HostingSignal

=head1 DESCRIPTION

Mimics the proprietary Cpanel::API module, dispatching
JSON-API (WHM API 1) and UAPI (cPanel) calls properly.

=cut

sub execute {
    my ($class, $apiversion, $module, $function, $args) = @_;
    
    my $result;
    
    if ($apiversion eq 'uapi') {
        $result = _dispatch_uapi($module, $function, $args);
    } elsif ($apiversion eq '1') {
        $result = _dispatch_whmapi1($module, $function, $args);
    } else {
        return format_error("Unsupported API version: $apiversion");
    }
    
    return to_json($result);
}

sub _dispatch_whmapi1 {
    my ($module, $function, $args) = @_;
    
    if ($module eq 'Accounts') {
        require Whostmgr::Accounts;
        if ($function eq 'createacct') {
            return format_whmapi1_response(Whostmgr::Accounts->create_account(%{$args}));
        } elsif ($function eq 'removeacct') {
            return format_whmapi1_response(Whostmgr::Accounts->remove_account($args->{user}));
        }
    } elsif ($module eq 'DNS') {
        require Whostmgr::DNS;
        if ($function eq 'addzonerecord') {
            return format_whmapi1_response(Whostmgr::DNS->add_zone_record(%{$args}));
        } elsif ($function eq 'parsezone') {
            return format_whmapi1_response(Whostmgr::DNS->parse_zone($args->{domain}));
        }
    } elsif ($module eq 'Web') {
        require Whostmgr::Web;
        if ($function eq 'rebuildhttpdconf') {
            return format_whmapi1_response(Whostmgr::Web->rebuild_httpd_conf());
        }
    } elsif ($module eq 'PHP') {
        require Whostmgr::PHP;
        if ($function eq 'set_vhost_version') {
            return format_whmapi1_response(Whostmgr::PHP->set_vhost_version(%{$args}));
        } elsif ($function eq 'get_system_default') {
            return format_whmapi1_response(Whostmgr::PHP->get_system_default());
        } elsif ($function eq 'list_installed_versions') {
            return format_whmapi1_response(Whostmgr::PHP->list_installed_versions());
        }
    } elsif ($module eq 'SSL') {
        require Whostmgr::SSL;
        if ($function eq 'install_autossl') {
            return format_whmapi1_response(Whostmgr::SSL->install_autossl(%{$args}));
        }
    }
    
    return format_error("Function $function not found in module $module for WHM API 1");
}

sub _dispatch_uapi {
    my ($module, $function, $args) = @_;
    
    if ($module eq 'Email') {
        require Cpanel::Email;
        if ($function eq 'add_pop') {
            return format_uapi_response(Cpanel::Email->add_pop(%{$args}));
        } elsif ($function eq 'delete_pop') {
            return format_uapi_response(Cpanel::Email->delete_pop(%{$args}));
        }
    } elsif ($module eq 'Ftp') {
        require Cpanel::FTP;
        if ($function eq 'add_ftp') {
            return format_uapi_response(Cpanel::FTP->add_ftp(%{$args}));
        } elsif ($function eq 'delete_ftp') {
            return format_uapi_response(Cpanel::FTP->delete_ftp(%{$args}));
        }
    } elsif ($module eq 'Fileman') {
        if ($function eq 'list_files') {
            # Mock fetching files from home directory
            my @mock_files = (
                { name => 'public_html', is_dir => 1, size => '4 KB', mod_time => '2026-03-01', perms => '0755' },
                { name => '.bashrc', is_dir => 0, size => '3.5 KB', mod_time => '2026-01-15', perms => '0644' },
                { name => '.profile', is_dir => 0, size => '807 B', mod_time => '2026-01-15', perms => '0644' }
            );
            return format_uapi_response({ dir => $args->{dir}, files => \@mock_files });
        }
    } elsif ($module eq 'Mysql') {
        require Cpanel::Mysql;
        if ($function eq 'create_database') {
            return format_uapi_response(Cpanel::Mysql->create_database(%{$args}));
        } elsif ($function eq 'create_user') {
            return format_uapi_response(Cpanel::Mysql->create_user(%{$args}));
        }
    } elsif ($module eq 'AddonDomain') {
        require Cpanel::Park;
        if ($function eq 'add_addon_domain') {
            return format_uapi_response(Cpanel::Park->add_addon_domain(%{$args}));
        }
    } elsif ($module eq 'Park') {
        require Cpanel::Park;
        if ($function eq 'add_parked_domain') {
            return format_uapi_response(Cpanel::Park->add_parked_domain(%{$args}));
        }
    } elsif ($module eq 'SSL') {
        require Whostmgr::SSL;
        if ($function eq 'get_cert_status') {
            return format_uapi_response(Whostmgr::SSL->get_cert_status($args->{domain}));
        }
    } elsif ($module eq 'AppInstaller') {
        require Cpanel::AppInstaller;
        if ($function eq 'install_wordpress') {
            return format_uapi_response(Cpanel::AppInstaller->install_wordpress(%{$args}));
        } elsif ($function eq 'list_installed') {
            return format_uapi_response(Cpanel::AppInstaller->list_installed($args->{user}));
        }
    }
    
    return format_error("Function $function not found in module $module for UAPI", 'uapi');
}

sub format_whmapi1_response {
    my ($data) = @_;
    return {
        metadata => {
            version => 1,
            result => $data->{success} || 0,
            reason => $data->{error} || $data->{message} || 'OK',
            command => 'unknown'
        },
        data => $data->{data} || {}
    };
}

sub format_uapi_response {
    my ($data) = @_;
    return {
        apiversion => 3,
        module => "Unknown",
        func => "unknown",
        status => $data->{success} || 0,
        errors => $data->{error} ? [$data->{error}] : undef,
        messages => $data->{message} ? [$data->{message}] : undef,
        data => $data
    };
}

sub format_error {
    my ($msg, $apitype) = @_;
    $apitype ||= '1';
    
    if ($apitype eq 'uapi') {
        return {
            status => 0,
            errors => [$msg],
            data => undef
        };
    } else {
        return {
            metadata => {
                result => 0,
                reason => $msg
            }
        };
    }
}

1; # End of module

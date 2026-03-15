package HS::Web;

use strict;
use warnings;
use File::Path qw(make_path remove_tree);

my $OLS_ROOT       = '/usr/local/lsws';
my $VHOST_CONF_DIR = "$OLS_ROOT/conf/vhosts";
my $MAIN_CONF      = "$OLS_ROOT/conf/httpd_config.conf";
my $WRAP_SYSOP     = '/usr/local/hspanel/bin/wrap_sysop';

sub rebuild_vhosts {
    my ($class, %args) = @_;

    my $reload = _reload_lsws();
    return {
        success     => $reload->{success},
        message     => $reload->{success} ? 'OpenLiteSpeed vhosts reloaded.' : $reload->{error},
        target_file => $MAIN_CONF,
    };
}

sub list_vhosts {
    my ($class, %args) = @_;

    return { success => 1, vhosts => [], total => 0 } unless -d $VHOST_CONF_DIR;

    opendir(my $dh, $VHOST_CONF_DIR) or return { success => 0, error => 'Unable to read vhost directory' };
    my @entries = grep { $_ ne '.' && $_ ne '..' } readdir($dh);
    closedir($dh);

    my @vhosts;
    for my $domain (sort @entries) {
        next unless -d "$VHOST_CONF_DIR/$domain";

        my $conf = "$VHOST_CONF_DIR/$domain/vhconf.conf";
        my $docroot = '';
        my $php = '';

        if (-f $conf) {
            open(my $fh, '<', $conf);
            while (my $line = <$fh>) {
                if ($line =~ /^docRoot\s+(\S+)/) {
                    $docroot = $1;
                }
                if ($line =~ /lsphp(\d+)/) {
                    $php = $1;
                }
            }
            close($fh);
        }

        push @vhosts, {
            domain  => $domain,
            docroot => $docroot,
            php     => ($php || 'unknown'),
            ssl     => (-f "/etc/letsencrypt/live/$domain/fullchain.pem" ? 1 : 0),
            status  => 'active',
        };
    }

    return { success => 1, vhosts => \@vhosts, total => scalar @vhosts };
}

sub create_vhost {
    my ($class, %args) = @_;

    my $domain = $args{domain} || return { success => 0, error => 'Missing domain' };
    my $user   = $args{user} || 'hspanel';
    my $docroot = $args{docroot} || "/home/$user/public_html";
    my $php     = $args{php} || '8.2';

    return { success => 0, error => 'Invalid domain' }
        unless $domain =~ /^(?!-)[A-Za-z0-9\-]{1,63}(?:\.[A-Za-z0-9\-]{1,63})+$/;

    make_path($docroot) unless -d $docroot;
    make_path("/home/$user/logs") unless -d "/home/$user/logs";

    my $vhost_dir = "$VHOST_CONF_DIR/$domain";
    make_path($vhost_dir) unless -d $vhost_dir;

    my $php_suffix = $php;
    $php_suffix =~ s/\.//g;
    my $php_bin = "$OLS_ROOT/lsphp$php_suffix/bin/php";
    $php_bin = "$OLS_ROOT/lsphp83/bin/php" unless -x $php_bin;

    my $conf_file = "$vhost_dir/vhconf.conf";
    open(my $cf, '>', $conf_file) or return { success => 0, error => 'Failed to write vhconf' };
    print $cf _render_vhconf($domain, $docroot, $php_bin, $user);
    close($cf);

    my $reg = _register_vhost($domain, $conf_file, "/home/$user/");
    return $reg unless $reg->{success};

    my $reload = _reload_lsws();
    return $reload unless $reload->{success};

    return {
        success => 1,
        message => "VirtualHost created for $domain (PHP $php).",
        domain  => $domain,
        docroot => $docroot,
    };
}

sub delete_vhost {
    my ($class, %args) = @_;
    my $domain = $args{domain} || return { success => 0, error => 'Missing domain' };

    my $vhost_dir = "$VHOST_CONF_DIR/$domain";
    remove_tree($vhost_dir) if -d $vhost_dir;

    _unregister_vhost($domain);
    my $reload = _reload_lsws();
    return $reload unless $reload->{success};

    return { success => 1, message => "VirtualHost for $domain removed." };
}

sub set_php_version {
    my ($class, %args) = @_;
    my $domain  = $args{domain}  || return { success => 0, error => 'Missing domain' };
    my $version = $args{version} || return { success => 0, error => 'Missing PHP version' };

    my $conf_file = "$VHOST_CONF_DIR/$domain/vhconf.conf";
    return { success => 0, error => 'Vhost config not found' } unless -f $conf_file;

    my $php_suffix = $version;
    $php_suffix =~ s/\.//g;
    my $php_bin = "$OLS_ROOT/lsphp$php_suffix/bin/php";
    return { success => 0, error => "lsphp$php_suffix binary not found" } unless -x $php_bin;

    open(my $in, '<', $conf_file) or return { success => 0, error => 'Unable to read vhost config' };
    my @lines = <$in>;
    close($in);

    for my $line (@lines) {
        $line =~ s|$OLS_ROOT/lsphp\d+/bin/php|$php_bin|g;
        $line =~ s/lsphp\d+\.sock/lsphp$php_suffix.sock/g;
    }

    open(my $out, '>', $conf_file) or return { success => 0, error => 'Unable to update vhost config' };
    print $out @lines;
    close($out);

    my $reload = _reload_lsws();
    return $reload unless $reload->{success};

    return { success => 1, message => "PHP version set to $version for $domain." };
}

sub _reload_lsws {
    my $rc = system($WRAP_SYSOP, 'reload_lsws');
    if ($rc != 0) {
        my @fallback_commands = (
            ['/usr/local/lsws/bin/lswsctrl', 'restart'],
            ['/bin/systemctl', 'reload', 'lsws'],
            ['/bin/systemctl', 'restart', 'lshttpd'],
            ['/bin/systemctl', 'restart', 'openlitespeed'],
        );

        for my $cmd (@fallback_commands) {
            my $fallback_rc = system(@$cmd);
            return { success => 1 } if $fallback_rc == 0;
        }

        return { success => 0, error => 'Failed to reload OpenLiteSpeed' };
    }
    return { success => 1 };
}

sub _register_vhost {
    my ($domain, $conf_file, $vh_root) = @_;

    return { success => 1, message => 'Main config missing, skipped registration' } unless -f $MAIN_CONF;

    open(my $fh, '<', $MAIN_CONF) or return { success => 0, error => 'Unable to read main OLS config' };
    my $content = do { local $/; <$fh> };
    close($fh);

    my $marker = "# vhost:$domain";
    return { success => 1 } if index($content, $marker) >= 0;

    my $entry = "\n$marker\n" .
        "virtualhost $domain {\n" .
        "  vhRoot                  $vh_root\n" .
        "  configFile              $conf_file\n" .
        "  allowSymbolLink         1\n" .
        "  enableScript            1\n" .
        "  restrained              0\n" .
        "  maxKeepAliveReq         500\n" .
        "}\n";

    open(my $out, '>', $MAIN_CONF) or return { success => 0, error => 'Unable to write main OLS config' };
    print $out $content . $entry;
    close($out);

    return { success => 1 };
}

sub _unregister_vhost {
    my ($domain) = @_;
    return unless -f $MAIN_CONF;

    open(my $fh, '<', $MAIN_CONF) or return;
    my $content = do { local $/; <$fh> };
    close($fh);

    $content =~ s/# vhost:\Q$domain\E\nvirtualhost \Q$domain\E \{.*?\n\}\n//sg;

    open(my $out, '>', $MAIN_CONF) or return;
    print $out $content;
    close($out);
}

sub _render_vhconf {
    my ($domain, $docroot, $php_bin, $user) = @_;
    return "# HS-Panel managed vhost\n" .
           "docRoot                   $docroot\n" .
           "vhDomain                  $domain\n" .
           "vhAliases                 www.$domain\n" .
           "adminEmails               admin\@$domain\n" .
           "\n" .
           "errorlog /home/$user/logs/error.log {\n" .
           "  useServer               0\n" .
           "  logLevel                WARN\n" .
           "  rollingSize             10M\n" .
           "}\n" .
           "\n" .
           "accesslog /home/$user/logs/access.log {\n" .
           "  useServer               0\n" .
           "  rollingSize             10M\n" .
           "}\n" .
           "\n" .
           "scripthandler  {\n" .
           "  add                     lsapi:${domain}_lsphp php\n" .
           "}\n" .
           "\n" .
           "extprocessor ${domain}_lsphp {\n" .
           "  type                    lsapi\n" .
           "  address                 uds://tmp/lshttpd/lsphp.sock\n" .
           "  path                    $php_bin\n" .
           "  extUser                 nobody\n" .
           "  extGroup                nobody\n" .
           "}\n" .
           "\n" .
           "rewrite  {\n" .
           "  enable                  1\n" .
           "  autoLoadHtaccess        1\n" .
           "}\n";
}

1;

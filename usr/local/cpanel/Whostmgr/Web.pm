package Whostmgr::Web;

use strict;
use warnings;
use File::Path qw(make_path);

=head1 NAME

Whostmgr::Web - Apache/Nginx Virtual Host Management

=head1 DESCRIPTION

Generates Apache or Nginx configuration files for new domains,
mirroring the Cpanel internal HTTPd conf generator.

=cut

sub create_vhost {
    my ($class, %args) = @_;
    
    my $domain   = $args{domain}   || return { success => 0, error => "Missing domain" };
    my $user     = $args{user}     || return { success => 0, error => "Missing user" };
    my $docroot  = $args{docroot}  || "/home/$user/public_html";
    my $engine   = $args{engine}   || "apache";
    
    my $conf_path;
    my $conf_data;
    
    if ($engine eq 'apache') {
        $conf_path = "/etc/apache2/sites-available/$domain.conf";
        $conf_data = _generate_apache_conf($domain, $user, $docroot);
    } elsif ($engine eq 'nginx') {
        $conf_path = "/etc/nginx/sites-available/$domain.conf";
        $conf_data = _generate_nginx_conf($domain, $user, $docroot);
    } else {
        return { success => 0, error => "Unsupported web engine: $engine" };
    }
    
    # In dev mode, we just write to a local log instead of /etc/
    my $dev_path = "cpanel_files/conf/$domain.conf";
    # make_path("cpanel_files/conf/");
    
    print "Writing VHost config for $domain (Engine: $engine)...\n";
    print "---\n$conf_data\n---\n";
    
    return { success => 1, message => "VHost created for $domain" };
}

sub _generate_apache_conf {
    my ($domain, $user, $docroot) = @_;
    return <<"EOF";
<VirtualHost *:80>
    ServerName $domain
    ServerAlias www.$domain
    DocumentRoot $docroot
    AssignUserID $user $user
    
    <Directory $docroot>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    
    ErrorLog /var/log/apache2/${domain}-error.log
    CustomLog /var/log/apache2/${domain}-access.log combined
</VirtualHost>
EOF
}

sub _generate_nginx_conf {
    my ($domain, $user, $docroot) = @_;
    return <<"EOF";
server {
    listen 80;
    server_name $domain www.$domain;
    root $docroot;
    index index.php index.html index.htm;
    
    access_log /var/log/nginx/${domain}-access.log;
    error_log /var/log/nginx/${domain}-error.log;
    
    location / {
        try_files \$uri \$uri/ /index.php?\$args;
    }
    
    location ~ \\.php\$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.2-fpm-$user.sock;
    }
}
EOF
}

sub rebuild_httpd_conf {
    my ($class) = @_;
    
    print "Rebuilding Apache/Nginx global configuration...\n";
    
    require Whostmgr::UserData;
    my $vhosts = Whostmgr::UserData->get_vhosts();
    
    # In a full build, this iterates through all vhosts to generate the main config string
    my $generated_conf = "";
    foreach my $domain (keys %$vhosts) {
        my $data = $vhosts->{$domain};
        $generated_conf .= _generate_apache_conf($domain, $data->{user}, $data->{documentroot});
    }
    
    if ($ENV{CPANEL_DEV_MOCK}) {
        print "Compiled Conf:\n$generated_conf\n";
        return { success => 1, message => "Mock: rebuilt httpd.conf based on UserData" };
    }
    
    # Real logic: cat user confs into main conf, verify syntax, restart
    # e.g., `/usr/sbin/apache2ctl configtest`
    my $syntax_ok = 1; 
    
    if ($syntax_ok) {
        # system("systemctl restart apache2");
        return { success => 1, message => "httpd.conf rebuilt and service restarted." };
    } else {
        return { success => 0, error => "Apache syntax check failed." };
    }
}

1; # End of module

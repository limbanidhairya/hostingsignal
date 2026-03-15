#!/usr/bin/perl
# hs-srvd.pl - HS-Panel Core HTTP/API Daemon
use strict;
use warnings;
use IO::Socket::INET;
use IO::Select;
use JSON;
use Data::Dumper;
use lib '/usr/local/hspanel/perl';

$| = 1; # Autoflush

my $PORT = 2086;
my $TEMPLATE_BASE = "/usr/local/hspanel/templates/ui";
my $API_LOG = "/usr/local/hspanel/logs/api.log";
my $ASSETS_BASE = "/usr/local/hspanel/templates/ui/assets";

print "Starting HS-Panel daemon (hs-srvd) on port $PORT...\n";

my $server = IO::Socket::INET->new(
    LocalAddr => '0.0.0.0',
    LocalPort => $PORT,
    Type      => SOCK_STREAM,
    Reuse     => 1,
    Listen    => 10
) or die "Couldn't bind port $PORT: $@\n";

my $sel = IO::Select->new($server);

while (my @ready = $sel->can_read) {
    foreach my $fh (@ready) {
        if ($fh == $server) {
            my $client = $server->accept();
            handle_client($client);
        }
    }
}

sub handle_client {
    my $client = shift;
    $client->autoflush(1);
    
    my $request_line = <$client>;
    return unless $request_line;
    
    my ($method, $path, $protocol) = split(/\s+/, $request_line);
    
    my %headers;
    my $content_length = 0;
    while(<$client>) {
        s/\r?\n$//;
        last if $_ eq "";
        if (my ($key, $val) = split(/:\s*/, $_, 2)) {
            $headers{lc($key)} = $val;
            $content_length = $val if lc($key) eq 'content-length';
        }
    }
    
    my $body = "";
    if ($content_length > 0) {
        read($client, $body, $content_length);
    }
    
    print "Handle request: $method $path\n";
    
    # ---------------------------
    # Static Asset Routing
    # ---------------------------
    if ($path =~ m|^/assets/([a-zA-Z0-9._\-/]+)$|) {
        my $rel = $1;
        if ($rel =~ /\.\./) {
            send_json($client, 400, { success => 0, error => "Invalid asset path" });
            close $client;
            return;
        }

        my $full = "$ASSETS_BASE/$rel";
        if (-f $full) {
            send_static_file($client, $full);
        } else {
            send_json($client, 404, { success => 0, error => "Asset not found" });
        }
    }
    # ---------------------------
    # API Routing
    # ---------------------------
    elsif ($path =~ m|^/api/([a-zA-Z0-9_\-]+)/([a-zA-Z0-9_\-]+)|) {
        my $module = $1;
        my $function = $2;
        
        my $payload = {};
        my $content_type = lc($headers{'content-type'} || '');
        if ($method eq 'POST' && $body) {
            if ($content_type =~ /application\/json/) {
                eval { $payload = decode_json($body); };
            } elsif ($content_type =~ /application\/x-www-form-urlencoded/) {
                $payload = parse_urlencoded_body($body);
            } else {
                # Fallback: attempt form parsing first, then JSON.
                $payload = parse_urlencoded_body($body);
                if (!%$payload) {
                    eval { $payload = decode_json($body); };
                }
            }
        }
        
        my $res = dispatch_api($module, $function, $payload);
        log_api_call($method, $path, $module, $function, $payload, $res);

        if ($method eq 'POST' && $content_type =~ /application\/x-www-form-urlencoded/) {
            my $redirect = $headers{referer} || _default_route_for_module($module);
            my $suffix = $res->{success}
                ? "ok=1"
                : "error=" . uri_escape($res->{error} || 'operation_failed');
            $redirect .= ($redirect =~ /\?/ ? '&' : '?') . $suffix;

            print $client "HTTP/1.1 302 Found\r\n";
            print $client "Location: $redirect\r\n";
            print $client "Connection: close\r\n\r\n";
        } else {
            send_json($client, 200, $res);
        }
    } 
    # ---------------------------
    # UI Routing
    # ---------------------------
    elsif ($path =~ m|^/login$| && $method eq 'POST') {
        my %form;
        if ($body) {
            foreach my $pair (split(/&/, $body)) {
                my ($k, $v) = split(/=/, $pair);
                $k =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
                $v =~ s/\+/ /g;
                $v =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
                $form{$k} = $v;
            }
        }

        # Load auth module from the panel Perl library path.
        my $loaded = eval {
            require HS::Account;
            1;
        };
        if (!$loaded) {
            send_json($client, 500, { success => 0, error => "Authentication module unavailable" });
            close $client;
            return;
        }

        my $auth_check = HS::Account->authenticate(username => $form{user}, password => $form{pass});
        
        if ($auth_check->{success}) {
            my $session_id = "hs_sess_" . time() . int(rand(1000));
            # In a real app we would map this session ID to the User ID in memory/DB
            print $client "HTTP/1.1 302 Found\r\n";
            print $client "Set-Cookie: hs_session=$session_id; Path=/; HttpOnly\r\n";
            print $client "Location: /dashboard\r\n\r\n";
        } else {
            print $client "HTTP/1.1 302 Found\r\n";
            print $client "Location: /login?error=1\r\n\r\n";
        }
    }
    elsif ($path eq '/logout') {
        print $client "HTTP/1.1 302 Found\r\n";
        print $client "Set-Cookie: hs_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT\r\n";
        print $client "Location: /\r\n\r\n";
    }
    elsif ($path =~ m|^/$| || $path =~ m|^/login|) {
        # parse GET query for error
        my $has_error = ($path =~ m/\?error=1/) ? 1 : 0;
        
        # if cookie hs_session exists, go to dashboard
        if (($headers{cookie} || '') =~ /hs_session=hs_sess_/) {
            print $client "HTTP/1.1 302 Found\r\nLocation: /dashboard\r\n\r\n";
        } else {
            send_html($client, 200, render_ui('login', { error => $has_error }));
        }
    }
    elsif ($path =~ m|^/software/([a-zA-Z0-9_\-]+)|) {
        my $app = $1;
        if (($headers{cookie} || '') !~ /hs_session=hs_sess_/) {
            print $client "HTTP/1.1 302 Found\r\nLocation: /\r\n\r\n";
        } else {
            if ($app eq 'phpmyadmin') {
                # Real phpMyAdmin runs via the HTTP web server, not inside this Perl daemon.
                print $client "HTTP/1.1 302 Found\r\nLocation: /phpmyadmin/\r\n\r\n";
                close $client;
                return;
            }

            my $sw_path = "usr/local/hspanel/software/$app/index.php";
            if (-f $sw_path) {
                my $php_content = do { local $/; open my $fh, '<', $sw_path; <$fh> };
                $php_content =~ s/<\?php//g;
                $php_content =~ s/\?>//g;
                $php_content =~ s/echo "(.*?)";/$1/g;
                $php_content =~ s/\/\/.+//g;
                
                my $html = "<!DOCTYPE html><html><head><title>HS-Panel Software ($app)</title><link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap' rel='stylesheet'><style>body{background:#0a1628;color:white;font-family:Inter,sans-serif;padding:50px;text-align:center;}a{color:#07b6d5;margin-top:20px;display:inline-block;}</style></head><body><div style='background:rgba(30,41,59,0.7);padding:40px;border-radius:12px;display:inline-block;border:1px solid rgba(51,65,85,0.5);'>$php_content<br><a href='/dashboard'>Return to Dashboard</a></div></body></html>";
                send_html($client, 200, $html);
            } else {
                send_html($client, 404, "Module not found.");
            }
        }
    }
    elsif ($path =~ m|^/admin$|) {
        # Protect routes
        if (($headers{cookie} || '') !~ /hs_session=hs_sess_/) {
            print $client "HTTP/1.1 302 Found\r\nLocation: /\r\n\r\n";
        } else {
            send_html($client, 200, render_ui('admin_dashboard'));
        }
    }
    elsif ($path =~ m|^/([a-z_]+)(\?.*)?$|) {
        my $route = $1;
        # Protect routes
        if (($headers{cookie} || '') !~ /hs_session=hs_sess_/) {
            print $client "HTTP/1.1 302 Found\r\nLocation: /\r\n\r\n";
        } else {
            my $html = eval { render_ui($route) };
            if ($@ || !$html) {
                # Fallback if template doesn't exist
                $html = render_ui('dashboard');
            }
            send_html($client, 200, $html);
        }
    }
    else {
        send_json($client, 404, { success => 0, error => "Not found" });
    }
    
    close $client;
}

sub dispatch_api {
    my ($module, $function, $args) = @_;

    ($module, $function) = _normalize_api_route($module, $function);
    
    my $mod_basename = ucfirst($module);
    $mod_basename = 'DNS' if $module eq 'dns';
    my $mod_full = "HS::$mod_basename";

    eval {
        require "HS/$mod_basename.pm";
        1;
    } or return { success => 0, error => "Unable to load module $mod_full" };
    if ($@) {
        return { success => 0, error => "Module $module not found." };
    }
    
    if (my $code = $mod_full->can($function)) {
        my $res = eval { $code->($mod_full, %$args) };
        if ($@) { return { success => 0, error => "Runtime error: $@" }; }
        return $res;
    } else {
        return { success => 0, error => "Function $function not found in $module." };
    }
}

sub _normalize_api_route {
    my ($module, $function) = @_;

    $module = lc($module || '');
    $function = lc($function || '');

    # Support dashed route/function names from external integrations.
    $module =~ s/-/_/g;
    $function =~ s/-/_/g;

    # Canonical module aliases.
    $module = 'mail' if $module eq 'email';
    $module = 'dns' if $module eq 'dns_zone';
    $module = 'ftp' if $module eq 'file_transfer';

    # Function aliases for compatibility.
    if ($module eq 'dns' && $function eq 'create_zone') {
        $function = 'rebuild_zone';
    }

    return ($module, $function);
}

sub parse_urlencoded_body {
    my ($raw) = @_;
    my %form;
    return {} unless defined $raw && length $raw;

    foreach my $pair (split(/&/, $raw)) {
        next unless length $pair;
        my ($k, $v) = split(/=/, $pair, 2);
        $k = '' unless defined $k;
        $v = '' unless defined $v;

        $k =~ tr/+/ /;
        $v =~ tr/+/ /;
        $k =~ s/%([a-fA-F0-9]{2})/pack('C', hex($1))/eg;
        $v =~ s/%([a-fA-F0-9]{2})/pack('C', hex($1))/eg;
        $form{$k} = $v;
    }

    return \%form;
}

sub _default_route_for_module {
    my ($module) = @_;
    $module = lc($module || '');

    return '/databases' if $module eq 'database';
    return '/email' if $module eq 'mail' || $module eq 'email';
    return '/domains' if $module eq 'domain' || $module eq 'web';
    return '/dns' if $module eq 'dns';
    return '/filemanager' if $module eq 'ftp';
    return '/dashboard';
}

sub uri_escape {
    my ($value) = @_;
    $value = '' unless defined $value;
    $value =~ s/([^A-Za-z0-9\-_.~])/sprintf("%%%02X", ord($1))/eg;
    return $value;
}

sub log_api_call {
    my ($method, $path, $module, $function, $payload, $res) = @_;

    my $dir = $API_LOG;
    $dir =~ s|/[^/]+$||;
    if (!-d $dir) {
        eval { mkdir $dir; };
    }

    my $payload_json = eval { to_json($payload || {}) } || '{}';
    my $result_json = eval { to_json($res || {}) } || '{}';
    my $stamp = scalar localtime();

    if (open(my $fh, '>>', $API_LOG)) {
        print $fh "[$stamp] $method $path module=$module function=$function payload=$payload_json result=$result_json\n";
        close($fh);
    }
}

sub send_json {
    my ($client, $code, $data) = @_;
    my $json = to_json($data);
    print $client "HTTP/1.1 $code OK\r\n";
    print $client "Content-Type: application/json\r\n";
    print $client "Connection: close\r\n\r\n";
    print $client $json;
}

sub send_html {
    my ($client, $code, $body) = @_;
    print $client "HTTP/1.1 $code OK\r\n";
    print $client "Content-Type: text/html; charset=UTF-8\r\n";
    print $client "Connection: close\r\n\r\n";
    print $client $body;
}

sub send_static_file {
    my ($client, $file_path) = @_;

    open(my $fh, '<', $file_path) or do {
        send_json($client, 404, { success => 0, error => "Asset not found" });
        return;
    };
    binmode($fh);
    my $content = do { local $/; <$fh> };
    close($fh);

    my $ctype = 'application/octet-stream';
    $ctype = 'image/png' if $file_path =~ /\.png$/i;
    $ctype = 'image/jpeg' if $file_path =~ /\.(jpg|jpeg)$/i;
    $ctype = 'image/svg+xml' if $file_path =~ /\.svg$/i;
    $ctype = 'image/webp' if $file_path =~ /\.webp$/i;
    $ctype = 'image/x-icon' if $file_path =~ /\.ico$/i;
    $ctype = 'text/css; charset=UTF-8' if $file_path =~ /\.css$/i;
    $ctype = 'application/javascript; charset=UTF-8' if $file_path =~ /\.js$/i;

    print $client "HTTP/1.1 200 OK\r\n";
    print $client "Content-Type: $ctype\r\n";
    print $client "Content-Length: " . length($content) . "\r\n";
    print $client "Cache-Control: public, max-age=300\r\n";
    print $client "Connection: close\r\n\r\n";
    print $client $content;
}

sub render_ui {
    my ($route, $extra_data) = @_;
    
    my $template_dir = "/usr/local/hspanel/templates/ui";
    
    # Map raw route to template name
    my $content_tmpl = "$route.tmpl";
    return undef unless -f "$template_dir/$content_tmpl";
    
    # Needs HTML::Template mapped locally or mocked
    my $html_content = "";
    open(my $fh, '<', "$template_dir/$content_tmpl") or die;
    $html_content = do { local $/; <$fh> };
    close($fh);
    
    my $master = "";
    open(my $mh, '<', "$template_dir/master.tmpl") or die;
    $master = do { local $/; <$mh> };
    close($mh);
    
    # Mock data bindings based on route
    my %data = (
        title        => ucfirst($route),
        user         => "hstpanel",
        user_initial  => "H",
        domain        => "hstpanel.com",
        contact_email => 'admin@hstpanel.com',
        "is_$route"   => "1"
    );
    
    # merge any extra data passed to render_ui
    if ($extra_data && ref($extra_data) eq 'HASH') {
        %data = (%data, %$extra_data);
    }
    
    if ($route eq 'dashboard') {
        %data = (%data, disk_used => 18.5, disk_total => 50.0, disk_percent => 37, bw_used => 122.4, bw_total => 1000, bw_percent => 12, active_domains => 5, active_emails => 12, email_disk => 245, cpu_percent => 23, ram_used => 6841, ram_total => 16384, ram_percent => 41.8, uptime => 'up 14 days');
    }
    elsif ($route eq 'domains') {
        my @vhosts;
        eval {
            require HS::Web;
            my $res = HS::Web->list_vhosts();
                my $domain_options = '';
                my $rows_html = '';
                if ($res->{success} && ref($res->{vhosts}) eq 'ARRAY') {
                    @vhosts = @{$res->{vhosts}};
                    my @domains = map { $_->{domain} } @vhosts;
                    $domain_options = join('', map { '<option value="' . _html_escape($_) . '">' . _html_escape($_) . '</option>' } @domains);

                    for my $item (@vhosts) {
                        my $domain = _html_escape($item->{domain} || '-');
                        my $docroot = _html_escape($item->{docroot} || '-');
                        my $php = _html_escape($item->{php} || 'unknown');
                        my $status = _html_escape($item->{status} || 'active');
                        my $ssl_badge = $item->{ssl}
                            ? '<span class="px-2 py-1 rounded bg-green-500/10 text-green-400 text-xs font-bold border border-green-500/20 flex items-center w-max gap-1"><span class="material-symbols-outlined text-[14px]">lock</span> Active</span>'
                            : '<span class="px-2 py-1 rounded bg-slate-500/10 text-slate-400 text-xs font-bold border border-slate-500/20 flex items-center w-max gap-1"><span class="material-symbols-outlined text-[14px]">lock_open</span> None</span>';

                        $rows_html .= qq{<tr class="hover:bg-slate-800/20 transition-colors">\n}
                                   . qq{<td class="px-6 py-4 font-bold text-slate-200">$domain</td>\n}
                                   . qq{<td class="px-6 py-4 font-mono text-slate-400 text-xs">$docroot</td>\n}
                                   . qq{<td class="px-6 py-4"><span class="px-2 py-1 rounded bg-purple-500/10 text-purple-400 text-xs font-bold border border-purple-500/20">$php</span></td>\n}
                                   . qq{<td class="px-6 py-4">$ssl_badge</td>\n}
                                   . qq{<td class="px-6 py-4"><span class="px-2 py-1 rounded bg-blue-500/10 text-blue-400 text-xs font-bold border border-blue-500/20">$status</span></td>\n}
                                   . qq{<td class="px-6 py-4 text-right">\n}
                                   . qq{<a href="/dns?domain=$domain" class="inline-flex items-center justify-center w-8 h-8 rounded bg-slate-800/50 hover:bg-slate-700 text-slate-300 transition-colors" title="DNS"><span class="material-symbols-outlined text-[18px]">dns</span></a>\n}
                                   . qq{</td>\n}
                                   . qq{</tr>\n};
                    }
                }
                $domain_options ||= '<option value="" disabled selected>No domains available</option>';
                $rows_html ||= '<tr><td colspan="6" class="px-6 py-6 text-sm text-slate-400">No domains provisioned yet.</td></tr>';
                $html_content =~ s/<TMPL_LOOP NAME=domains>.*?<\/TMPL_LOOP>/$rows_html/gs;
                $data{domain_options} = $domain_options;
                1;
            };
    }
    elsif ($route eq 'databases') {
        eval {
            require HS::Database;
            my $db_res = HS::Database->list_databases();
            if ($db_res->{success}) {
                my $dbs_html = '';
                for my $db (@{$db_res->{databases}}) {
                    $dbs_html .= qq{<tr class="hover:bg-slate-800/20 transition-colors">}
                              . qq{<td class="px-6 py-4 font-bold text-slate-200">}.$db->{name}.qq{</td>}
                              . qq{<td class="px-6 py-4 font-mono text-slate-400 text-xs">}.$db->{size_mb}.qq{ MB</td>}
                              . qq{<td class="px-6 py-4">}.$db->{tables}.qq{</td>}
                              . qq{<td class="px-6 py-4 text-right">}
                              . qq{<button class="inline-flex items-center justify-center w-8 h-8 rounded bg-red-500/10 hover:bg-red-500/20 text-red-500 transition-colors" title="Delete"><span class="material-symbols-outlined text-[18px]">delete</span></button>}
                              . qq{</td></tr>};
                }
                $dbs_html ||= '<tr><td colspan="4" class="px-6 py-10 text-center text-slate-500">No databases configured</td></tr>';
                $html_content =~ s/<TMPL_LOOP NAME=databases>.*?<\/TMPL_LOOP>/$dbs_html/gs;
            }

            my $u_res = HS::Database->list_users();
            if ($u_res->{success}) {
                my $users_html = '';
                for my $u (@{$u_res->{users}}) {
                    $users_html .= qq{<tr class="hover:bg-slate-800/20 transition-colors">}
                                . qq{<td class="px-6 py-4 font-bold text-slate-200">}.$u->{username}.qq{</td>}
                                . qq{<td class="px-6 py-4 font-mono text-slate-400 text-xs">}.$u->{host}.qq{</td>}
                                . qq{<td class="px-6 py-4 text-right">}
                                . qq{<button class="inline-flex items-center justify-center w-8 h-8 rounded bg-slate-800/50 hover:bg-slate-700 text-slate-300 transition-colors" title="Change Password"><span class="material-symbols-outlined text-[18px]">key</span></button>}
                                . qq{<button class="inline-flex items-center justify-center w-8 h-8 rounded bg-red-500/10 hover:bg-red-500/20 text-red-500 transition-colors" title="Delete"><span class="material-symbols-outlined text-[18px]">delete</span></button>}
                                . qq{</td></tr>};
                }
                $users_html ||= '<tr><td colspan="3" class="px-6 py-10 text-center text-slate-500">No database users configured</td></tr>';
                $html_content =~ s/<TMPL_LOOP NAME=users>.*?<\/TMPL_LOOP>/$users_html/gs;
            }
            1;
        };
    }
    elsif ($route eq 'dns_editor') {
        eval {
            require HS::Web;
            require HS::DNS;
            my $v_res = HS::Web->list_vhosts();
            my @opts;
            my $curr = $extra_data->{domain} || ($v_res->{success} ? $v_res->{vhosts}[0]{domain} : undef);
            for my $v (@{$v_res->{vhosts} || []}) {
                my $sel = ($v->{domain} eq $curr) ? 'selected' : '';
                push @opts, qq{<option value="$v->{domain}" $sel>$v->{domain}</option>};
            }
            $data{domain_options} = join('', @opts);
            $data{current_domain} = $curr;

            if ($curr) {
                my $z_res = HS::DNS->list_zones(); # Simplified lookup
                # Logic to fetch records for specific domain...
                my $records_html = '';
                # Mocking records for now or fetch from real zone file if implemented
                $records_html ||= '<tr><td colspan="5" class="px-6 py-10 text-center text-slate-500">No DNS records found</td></tr>';
                $html_content =~ s/<TMPL_LOOP NAME=records>.*?<\/TMPL_LOOP>/$records_html/gs;
            }
            1;
        };
    }
    elsif ($route eq 'cron') {
        eval {
            require HS::Cron;
            my $res = HS::Cron->list_jobs();
            if ($res->{success}) {
                my $rows = '';
                for my $j (@{$res->{jobs}}) {
                    my $sched = "$j->{minute} $j->{hour} $j->{day} $j->{month} $j->{weekday}";
                    $rows .= qq{<tr class="hover:bg-slate-800/20 transition-colors">}
                          . qq{<td class="px-6 py-4 font-mono font-bold text-primary">$sched</td>}
                          . qq{<td class="px-6 py-4 font-mono text-slate-300 break-all">$j->{command}</td>}
                          . qq{<td class="px-6 py-4 text-right space-x-2">}
                          . qq{<button class="inline-flex items-center justify-center w-8 h-8 rounded bg-slate-800/50 hover:bg-slate-700 text-slate-300 transition-colors"><span class="material-symbols-outlined text-[18px]">edit</span></button>}
                          . qq{<button class="inline-flex items-center justify-center w-8 h-8 rounded bg-red-500/10 hover:bg-red-500/20 text-red-500 transition-colors"><span class="material-symbols-outlined text-[18px]">delete</span></button>}
                          . qq{</td></tr>};
                }
                $rows ||= '<tr><td colspan="3" class="px-6 py-10 text-center text-slate-500">No cron jobs configured</td></tr>';
                $html_content =~ s/<TMPL_LOOP NAME=cron_jobs>.*?<\/TMPL_LOOP>/$rows/gs;
            }
            1;
        };
    }
    elsif ($route eq 'backups') {
        eval {
            require HS::Backup;
            my $res = HS::Backup->list_backups();
            if ($res->{success}) {
                my $rows = '';
                for my $b (@{$res->{backups}}) {
                    $rows .= qq{<tr class="hover:bg-slate-800/20 transition-colors">}
                          . qq{<td class="px-6 py-4 font-mono font-bold text-slate-200">$b->{date}</td>}
                          . qq{<td class="px-6 py-4"><span class="px-2 py-1 rounded bg-blue-500/10 text-blue-400 text-xs font-bold border border-blue-500/20">$b->{type}</span></td>}
                          . qq{<td class="px-6 py-4 text-slate-400">$b->{size_mb} MB</td>}
                          . qq{<td class="px-6 py-4"><span class="px-2 py-1 rounded bg-green-500/10 text-green-400 text-xs font-bold border border-green-500/20">$b->{status}</span></td>}
                          . qq{<td class="px-6 py-4 text-right space-x-2">}
                          . qq{<button class="inline-flex items-center justify-center w-8 h-8 rounded bg-slate-800/50 hover:bg-primary/20 hover:text-primary text-slate-300 transition-colors"><span class="material-symbols-outlined text-[18px]">download</span></button>}
                          . qq{<button class="inline-flex items-center justify-center w-8 h-8 rounded bg-slate-800/50 hover:bg-amber-500/20 hover:text-amber-500 text-slate-300 transition-colors"><span class="material-symbols-outlined text-[18px]">restore</span></button>}
                          . qq{<button class="inline-flex items-center justify-center w-8 h-8 rounded bg-red-500/10 hover:bg-red-500/20 text-red-500 transition-colors"><span class="material-symbols-outlined text-[18px]">delete</span></button>}
                          . qq{</td></tr>};
                }
                $rows ||= '<tr><td colspan="5" class="px-6 py-10 text-center text-slate-500">No backups found</td></tr>';
                $html_content =~ s/<TMPL_LOOP NAME=backups>.*?<\/TMPL_LOOP>/$rows/gs;
            }
            1;
        };
    }
    elsif ($route eq 'email') {
        eval {
            require HS::Mail;
            my $res = HS::Mail->list_accounts();
            if ($res->{success}) {
                my $rows = '';
                for my $acc (@{$res->{accounts}}) {
                    $rows .= qq{<tr class="hover:bg-slate-800/20 transition-colors">}
                          . qq{<td class="px-6 py-4 font-bold text-slate-200">$acc->{email}</td>}
                          . qq{<td class="px-6 py-4 font-mono text-slate-400 text-xs">$acc->{used_mb} / $acc->{quota_mb} MB</td>}
                          . qq{<td class="px-6 py-4"><span class="px-2 py-1 rounded bg-blue-500/10 text-blue-400 text-xs font-bold border border-blue-500/20">$acc->{status}</span></td>}
                          . qq{<td class="px-6 py-4 text-right space-x-2">}
                          . qq{<button class="inline-flex items-center justify-center w-8 h-8 rounded bg-slate-800/50 hover:bg-slate-700 text-slate-300 transition-colors"><span class="material-symbols-outlined text-[18px]">key</span></button>}
                          . qq{<button class="inline-flex items-center justify-center w-8 h-8 rounded bg-red-500/10 hover:bg-red-500/20 text-red-500 transition-colors"><span class="material-symbols-outlined text-[18px]">delete</span></button>}
                          . qq{</td></tr>};
                }
                $rows ||= '<tr><td colspan="4" class="px-6 py-10 text-center text-slate-500">No email accounts configured</td></tr>';
                $html_content =~ s/<TMPL_LOOP NAME=accounts>.*?<\/TMPL_LOOP>/$rows/gs;
            }
            1;
        };
    }
    elsif ($route eq 'admin_dashboard') {
        %data = (%data, total_accounts => 247, total_domains => 892, cpu_percent => 34, ram_percent => 62, ram_used => 9.92, ram_total => 16.0, disk_percent => 75);
    }
    
    # Naive poor-man's template replacement since HTML::Template might not be installed on Windows
    for my $k (keys %data) {
        my $val = $data{$k};
        $html_content =~ s/<TMPL_VAR NAME=$k>/$val/g;
        $master =~ s/<TMPL_VAR NAME=$k>/$val/g;
    }
    
    $html_content = _apply_template_conditionals($html_content, \%data);
    $master = _apply_template_conditionals($master, \%data);
    
    # Clean up loops/ifs in content
    $html_content =~ s/<TMPL_LOOP.*?>.*?<\/TMPL_LOOP>//gs;
    $html_content =~ s/<TMPL_IF.*?>.*?<\/TMPL_IF>//gs;
    $html_content =~ s/<TMPL_UNLESS.*?>.*?<\/TMPL_UNLESS>//gs;
    
    if ($route eq 'login') {
        return $html_content;
    }
    
    $master =~ s/<TMPL_VAR NAME=content>/$html_content/g;
    $master =~ s/<TMPL_IF.*?>.*?<\/TMPL_IF>//gs;
    $master =~ s/<TMPL_UNLESS.*?>.*?<\/TMPL_UNLESS>//gs;
    
    return $master;
}

sub _apply_template_conditionals {
    my ($template, $data_ref) = @_;
    return $template unless defined $template;
    return $template unless $data_ref && ref($data_ref) eq 'HASH';

    my $max_passes = 25;
    while ($max_passes-- > 0) {
        my $previous = $template;

        $template =~ s{<TMPL_IF\s+NAME=([a-zA-Z0-9_]+)\s*>(.*?)(?:<TMPL_ELSE>(.*?))?<\/TMPL_IF>}{
            my ($name, $if_block, $else_block) = ($1, $2, $3);
            my $value = exists $data_ref->{$name} ? $data_ref->{$name} : undef;
            my $truthy = defined($value) && $value ne '' && $value ne '0';
            $truthy ? $if_block : (defined($else_block) ? $else_block : '');
        }gse;

        $template =~ s{<TMPL_UNLESS\s+NAME=([a-zA-Z0-9_]+)\s*>(.*?)(?:<TMPL_ELSE>(.*?))?<\/TMPL_UNLESS>}{
            my ($name, $unless_block, $else_block) = ($1, $2, $3);
            my $value = exists $data_ref->{$name} ? $data_ref->{$name} : undef;
            my $truthy = defined($value) && $value ne '' && $value ne '0';
            $truthy ? (defined($else_block) ? $else_block : '') : $unless_block;
        }gse;

        last if $template eq $previous;
    }

    return $template;
}

sub _html_escape {
    my ($value) = @_;
    $value = '' unless defined $value;
    $value =~ s/&/&amp;/g;
    $value =~ s/</&lt;/g;
    $value =~ s/>/&gt;/g;
    $value =~ s/"/&quot;/g;
    $value =~ s/'/&#39;/g;
    return $value;
}

1;

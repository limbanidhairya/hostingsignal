#!/usr/bin/perl
# hs-taskd.pl - HS-Panel Background Job Queue Processor
use strict;
use warnings;
use JSON;
use File::Basename;
use File::Path qw(make_path);
use Time::HiRes qw(time);

$| = 1;

my $QUEUE_DIR = "/var/hspanel/queue";
my $DONE_DIR  = "/var/hspanel/queue/done";
my $SCRIPTS_DIR = "/usr/local/hspanel/scripts";

# Windows Mock Path Fixes
if (!-d $QUEUE_DIR && -d "cpanel_files/var/hspanel/queue") {
    $QUEUE_DIR = "cpanel_files/var/hspanel/queue";
    $DONE_DIR  = "cpanel_files/var/hspanel/queue/done";
}

make_path($QUEUE_DIR) unless -d $QUEUE_DIR;
make_path($DONE_DIR) unless -d $DONE_DIR;

print "Starting HS-Panel Task Daemon (hs-taskd). Watching $QUEUE_DIR\n";

while (1) {
    # Scan for jobs (JSON files)
    my @jobs = glob("$QUEUE_DIR/*.json");
    
    foreach my $job_file (@jobs) {
        process_job($job_file);
    }
    
    sleep(2); # Poll interval
}

sub process_job {
    my ($file) = @_;

    print "Processing Job: $file\n";

    # Basic lock-by-rename to avoid duplicate processing across daemons.
    my $processing_file = $file;
    $processing_file =~ s/\.json$/.processing/;
    return unless rename($file, $processing_file);

    open(my $fh, '<', $processing_file) or return;
    my $json_text = do { local $/; <$fh> };
    close($fh);
    
    my $payload;
    eval { $payload = decode_json($json_text); };
    if ($@) {
        print "Bad JSON in $processing_file: $@\n";
        unlink($processing_file);
        return;
    }

    my $job_id = $payload->{id} || basename($processing_file);
    my $action = $payload->{type} || $payload->{action} || '';
    my $args = $payload->{args} || $payload;
    my $started = time;

    print "Executing Background Task: $action ($job_id)\n";

    my $result = _dispatch_task($action, $args);
    $result->{success} = $result->{success} ? JSON::true : JSON::false;
    $result->{id} = $job_id;
    $result->{action} = $action;
    $result->{duration_ms} = int((time - $started) * 1000);
    $result->{finished_at} = time;

    my $base = basename($processing_file);
    $base =~ s/\.processing$/.json/;
    my $done_path = "$DONE_DIR/$base";
    my $out_json = "$DONE_DIR/$base.result.json";

    rename($processing_file, $done_path);
    if (open(my $out, '>', $out_json)) {
        print $out to_json($result, { pretty => 1 });
        close($out);
    }
}

sub _dispatch_task {
    my ($action, $args) = @_;

    if ($action eq 'generate_backup') {
        return _task_generate_backup($args);
    }
    if ($action eq 'rebuild_httpd') {
        return _task_run_script('rebuild_httpd.sh', $args);
    }
    if ($action eq 'rebuild_dns') {
        return _task_run_script('rebuild_dns.sh', $args);
    }
    if ($action eq 'rebuild_mail') {
        return _task_run_script('rebuild_mail.sh', $args);
    }
    if ($action eq 'restart_services') {
        return _task_run_script('restart_services.sh', $args);
    }
    if ($action eq 'ssl_renew') {
        return _task_run_script('ssl_renew.sh', $args);
    }
    if ($action eq 'quota_sync') {
        return _task_run_script('quota_sync.sh', $args);
    }
    if ($action eq 'ip_block') {
        return _task_run_script('ip_block.sh', $args);
    }
    if ($action eq 'cleanup_tmp') {
        return _task_run_script('cleanup_tmp.sh', $args);
    }
    if ($action eq 'whmcs_create_account') {
        $args->{mode} = 'create';
        return _task_run_script('whmcs_provision.sh', $args);
    }
    if ($action eq 'whmcs_suspend_account') {
        $args->{mode} = 'suspend';
        return _task_run_script('whmcs_provision.sh', $args);
    }
    if ($action eq 'whmcs_unsuspend_account') {
        $args->{mode} = 'unsuspend';
        return _task_run_script('whmcs_provision.sh', $args);
    }
    if ($action eq 'whmcs_terminate_account') {
        $args->{mode} = 'terminate';
        return _task_run_script('whmcs_provision.sh', $args);
    }

    return {
        success => 0,
        error   => "Unsupported action: $action",
    };
}

sub _task_generate_backup {
    my ($args) = @_;
    my $user = $args->{username} || $args->{user} || '';
    return { success => 0, error => 'Missing username for backup' } unless $user;

    my $backup_dir = "/var/hspanel/backups";
    make_path($backup_dir) unless -d $backup_dir;

    my $archive = "$backup_dir/${user}_" . int(time) . ".tar.gz";
    my $source = "/home/$user";

    my $cmd = "tar -czf '$archive' '$source' 2>&1";
    my $out = `$cmd`;
    my $rc = $? >> 8;
    if ($rc != 0) {
        return { success => 0, error => "Backup failed: $out" };
    }

    return {
        success => 1,
        message => "Backup completed",
        archive => $archive,
    };
}

sub _task_run_script {
    my ($script, $args) = @_;
    my $path = "$SCRIPTS_DIR/$script";

    return { success => 0, error => "Script not found: $path" }
        unless -x $path;

    my @kv;
    for my $k (sort keys %$args) {
        next if ref($args->{$k});
        my $v = $args->{$k};
        next unless defined $v;
        push @kv, "$k='$v'";
    }
    my $arg_str = join(' ', @kv);

    my $cmd = "$path $arg_str 2>&1";
    my $out = `$cmd`;
    my $rc = $? >> 8;

    return {
        success => ($rc == 0 ? 1 : 0),
        message => ($rc == 0 ? 'Task completed' : 'Task failed'),
        output  => $out,
        script  => $script,
        exit_code => $rc,
    };
}

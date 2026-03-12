package HS::Filemanager;
use strict;
use warnings;
use File::Basename;
use File::Path qw(make_path remove_tree);
use File::Spec;

# Determine the base path for users, mimicking /home/
my $BASE_DIR = "/usr/local/hspanel/userdata";

# Helper to normalize and ensure safety of requested paths
sub get_safe_path {
    my ($user, $rel_path) = @_;
    $user ||= "hstpanel"; # fallback mock user
    
    # Create base user directory if it doesn't exist
    my $user_dir = "$BASE_DIR/$user";
    if (!-d $user_dir) {
        make_path($user_dir);
        make_path("$user_dir/public_html");
    }
    
    $rel_path ||= "/";
    $rel_path =~ s/\.\.//g; # basic sanitization against directory traversal
    
    # Clean up double slashes
    my $full_path = File::Spec->canonpath("$user_dir/$rel_path");
    
    # Ensure it's still within user dir
    if (index($full_path, $user_dir) != 0) {
        return $user_dir; # Fallback securely
    }
    
    return $full_path;
}

sub list_files {
    my ($class, %args) = @_;
    my $path = get_safe_path($args{user}, $args{path});
    
    if (!-d $path) {
        return { success => 0, error => "Directory does not exist." };
    }
    
    opendir(my $dh, $path) or return { success => 0, error => "Could not open directory: $!" };
    my @files = readdir($dh);
    closedir($dh);
    
    my @items;
    
    foreach my $file (@files) {
        next if $file eq '.' || $file eq '..';
        
        my $full_file = "$path/$file";
        my ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,$atime,$mtime,$ctime,$blksize,$blocks) = stat($full_file);
        
        my $is_dir = -d $full_file ? 1 : 0;
        
        # Simple permissions string
        my $perms = sprintf "%04o", $mode & 07777;
        
        push @items, {
            name => $file,
            is_dir => $is_dir,
            size => $size,
            perms => $perms,
            modified => $mtime
        };
    }
    
    # Sort: directories first, then alphabetically
    @items = sort { 
        ($b->{is_dir} <=> $a->{is_dir}) || (lc($a->{name}) cmp lc($b->{name}))
    } @items;
    
    return {
        success => 1,
        path => $args{path} || "/",
        items => \@items
    };
}

sub create_folder {
    my ($class, %args) = @_;
    my $parent_path = get_safe_path($args{user}, $args{path});
    my $new_folder = $args{name};
    
    if (!$new_folder || $new_folder =~ m|/|) {
        return { success => 0, error => "Invalid folder name." };
    }
    
    my $full_path = "$parent_path/$new_folder";
    
    if (-e $full_path) {
        return { success => 0, error => "Item already exists." };
    }
    
    eval { make_path($full_path); };
    if ($@) {
        return { success => 0, error => "Failed to create folder: $@" };
    }
    
    return { success => 1, message => "Folder created successfully." };
}

sub create_file {
    my ($class, %args) = @_;
    my $parent_path = get_safe_path($args{user}, $args{path});
    my $new_file = $args{name};
    
    if (!$new_file || $new_file =~ m|/|) {
        return { success => 0, error => "Invalid file name." };
    }
    
    my $full_path = "$parent_path/$new_file";
    
    if (-e $full_path) {
        return { success => 0, error => "Item already exists." };
    }
    
    if (open(my $fh, '>', $full_path)) {
        close($fh);
        return { success => 1, message => "File created successfully." };
    } else {
        return { success => 0, error => "Failed to create file: $!" };
    }
}

sub delete_item {
    my ($class, %args) = @_;
    my $path = get_safe_path($args{user}, $args{path});
    
    if (!-e $path) {
        return { success => 0, error => "Item does not exist." };
    }
    
    if (-d $path) {
        remove_tree($path);
    } else {
        unlink($path);
    }
    
    return { success => 1, message => "Deleted successfully." };
}

sub read_file {
    my ($class, %args) = @_;
    my $path = get_safe_path($args{user}, $args{path});
    
    if (!-f $path) {
        return { success => 0, error => "File does not exist or is a directory." };
    }
    
    if (open(my $fh, '<', $path)) {
        my $content = do { local $/; <$fh> };
        close($fh);
        return { success => 1, content => $content };
    } else {
        return { success => 0, error => "Failed to read file: $!" };
    }
}

sub write_file {
    my ($class, %args) = @_;
    my $path = get_safe_path($args{user}, $args{path});
    my $content = $args{content} || "";
    
    if (-d $path) {
        return { success => 0, error => "Cannot write to a directory." };
    }
    
    if (open(my $fh, '>', $path)) {
        print $fh $content;
        close($fh);
        return { success => 1, message => "File saved successfully." };
    } else {
        return { success => 0, error => "Failed to write file: $!" };
    }
}

1;

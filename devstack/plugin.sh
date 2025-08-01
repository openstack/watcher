# plugin.sh - DevStack plugin script to install watcher

# Save trace setting
_XTRACE_WATCHER_PLUGIN=$(set +o | grep xtrace)
set -o xtrace

echo_summary "watcher's plugin.sh was called..."
. $DEST/watcher/devstack/lib/watcher

# Show all of defined environment variables
(set -o posix; set)

if is_service_enabled watcher-api watcher-decision-engine watcher-applier; then
    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        echo_summary "Before Installing watcher"
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing watcher"
        install_watcher

        LIBS_FROM_GIT="${LIBS_FROM_GIT},python-watcherclient"

        install_watcherclient
        cleanup_watcher
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring watcher"
        configure_watcher

        if is_service_enabled key; then
            create_watcher_accounts
        fi

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize watcher
        init_watcher

        # Start the watcher components
        echo_summary "Starting watcher"
        start_watcher
    elif [[ "$1" == "stack" && "$2" == "test-config" ]]; then
        echo_summary "Configuring tempest for watcher"
        configure_tempest_for_watcher
    fi

    if [[ "$1" == "unstack" ]]; then
        stop_watcher
    fi

    if [[ "$1" == "clean" ]]; then
        cleanup_watcher
    fi
fi

# Restore xtrace
$_XTRACE_WATCHER_PLUGIN

#!/usr/bin/env bash

# ``upgrade-watcher``

echo "*********************************************************************"
echo "Begin $0"
echo "*********************************************************************"

# Clean up any resources that may be in use
cleanup() {
    set +o errexit

    echo "********************************************************************"
    echo "ERROR: Abort $0"
    echo "********************************************************************"

    # Kill ourselves to signal any calling process
    trap 2; kill -2 $$
}

trap cleanup SIGHUP SIGINT SIGTERM

# Keep track of the grenade directory
RUN_DIR=$(cd $(dirname "$0") && pwd)

# Source params
source $GRENADE_DIR/grenaderc

# Import common functions
source $GRENADE_DIR/functions

# This script exits on an error so that errors don't compound and you see
# only the first error that occurred.
set -o errexit

# Upgrade watcher
# ============

# Get functions from current DevStack
source $TARGET_DEVSTACK_DIR/stackrc
source $TARGET_DEVSTACK_DIR/lib/apache
source $TARGET_DEVSTACK_DIR/lib/tls
source $TARGET_DEVSTACK_DIR/lib/keystone

source $TOP_DIR/openrc admin admin

source $(dirname $(dirname $BASH_SOURCE))/settings
source $(dirname $(dirname $BASH_SOURCE))/plugin.sh

# Print the commands being run so that we can see the command that triggers
# an error.  It is also useful for following allowing as the install occurs.
set -o xtrace

# Save current config files for posterity
[[ -d $SAVE_DIR/etc.watcher ]] || cp -pr $WATCHER_CONF_DIR $SAVE_DIR/etc.watcher

# Install the target watcher
install_watcher

# calls upgrade-watcher for specific release
upgrade_project watcher $RUN_DIR $BASE_DEVSTACK_BRANCH $TARGET_DEVSTACK_BRANCH

if [[ ! -f "$WATCHER_UWSGI_CONF" ]] && [[ "$WATCHER_USE_WSGI_MODE" == "uwsgi" ]]
then write_uwsgi_config "$WATCHER_UWSGI_CONF" "$WATCHER_UWSGI" "/infra-optim"
     endpoints=$(openstack endpoint list --service watcher -c ID -f value)
     for id in $endpoints; do
         openstack endpoint delete $id
     done
     create_watcher_accounts
fi

# Migrate the database
watcher-db-manage upgrade || die $LINO "DB migration error"

start_watcher

# Don't succeed unless the services come up
ensure_services_started watcher-api watcher-decision-engine watcher-applier

set +o xtrace
echo "*********************************************************************"
echo "SUCCESS: End $0"
echo "*********************************************************************"

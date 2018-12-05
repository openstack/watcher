#!/bin/bash

set -o errexit

source $GRENADE_DIR/grenaderc
source $GRENADE_DIR/functions

source $TOP_DIR/openrc admin demo

set -o xtrace

function _wait_for_status {
     while :
     do
         state=$("${@:2}" -f value -c State)
         [[ $state == "SUCCEEDED" ]] && break
         if [ $state == "ERROR" ]; then
             die $LINENO "ERROR creating audit"
         fi
         sleep 10
     done
 }

function create_audit_template {
    at_id=$(openstack optimize audittemplate create d1 dummy -s dummy -f value -c UUID)
    resource_save watcher at_id $at_id
 }

function create_audit {
    audit_id=$(openstack optimize audit create -s dummy -g dummy -f value -c UUID)
    resource_save watcher audit_id $audit_id
}

function create_audit_with_autotrigger {
    audit_at_id=$(openstack optimize audit create -s dummy -g dummy -f value -c UUID --auto-trigger)
    resource_save watcher audit_at_id $audit_at_id
}

function verify_audit_template {
    local at_id=$(resource_get watcher at_id)
    openstack optimize audittemplate show $at_id
}

function verify_audit_with_autotrigger {
    local audit_at_id=$(resource_get watcher audit_at_id)
    _wait_for_status "SUCCEEDED" openstack optimize audit show $audit_at_id
    local actionplan_at_id=$(openstack optimize actionplan list --audit $audit_at_id -c UUID -f value)
    resource_save watcher actionplan_at $actionplan_at_id
    actionplan_at_state=$(openstack optimize actionplan show $actionplan_at_id -c State -f value)
    if [ $actionplan_at_state != "SUCCEEDED" ]; then
        die $LINENO "ERROR executing actionplan"
    fi
}

function verify_audit {
    local audit_id=$(resource_get watcher audit_id)
    _wait_for_status "SUCCEEDED" openstack optimize audit show $audit_id
    local actionplan_id=$(openstack optimize actionplan list --audit $audit_id -c UUID -f value)
    resource_save watcher actionplan $actionplan_id
    actionplan_state=$(openstack optimize actionplan show $actionplan_id -c State -f value)
    if [ $actionplan_state != "RECOMMENDED" ]; then
        die $LINENO "ERROR creating actionplan"
    fi
}

function verify_noapi {
    # currently no good way
    :
}

function delete_audit {
  local audit_id=$(resource_get watcher audit_id)
  local actionplan_id=$(resource_get watcher actionplan)
  watcher actionplan delete $actionplan_id
  openstack optimize audit delete $audit_id
}

function delete_audit_with_autotrigger {
  local audit_at_id=$(resource_get watcher audit_at_id)
  local actionplan_id=$(resource_get watcher actionplan_at)
  watcher actionplan delete $actionplan_id
  openstack optimize audit delete $audit_at_id
}

function delete_audit_template {
  local at_id=$(resource_get watcher at_id)
  openstack optimize audittemplate delete $at_id
}

function create {
  create_audit_template
  create_audit
  create_audit_with_autotrigger
}

function verify {
  verify_audit_template
  verify_audit
  verify_audit_with_autotrigger
}

function destroy {
  delete_audit_template
  delete_audit
  delete_audit_with_autotrigger
}

# Dispatcher
case $1 in
    "create")
        create
        ;;
    "verify_noapi")
        verify_noapi
        ;;
    "verify")
        verify
        ;;
    "destroy")
        destroy
        ;;
    "force_destroy")
        set +o errexit
        destroy
        ;;
esac

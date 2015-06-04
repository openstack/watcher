# Watcher Decision Engine

This component is responsible for computing a list of potential optimization actions in order to fulfill the goals of an audit. 

It uses the following input data :
* current, previous and predicted state of the cluster (hosts, instances, network, ...)
* evolution of metrics within a time frame

It first selects the most appropriate optimization strategy depending on several factors :
* the optimization goals that must be fulfilled (servers consolidation, energy consumption, license optimization, ...)
* the deadline that was provided by the Openstack cluster admin for delivering an action plan
* the "aggressivity" level regarding potential optimization actions :
  * is it allowed to do a lot of instance migrations ?
  * is it allowed to consume a lot of bandwidth on the admin network ?
  * is it allowed to violate initial placement constraint such as affinity/anti-affinity, region, ... ? 

The strategy is then executed and generates a list of Meta-Actions in order to fulfill the goals of the Audit. 

A Meta-Action is a generic optimization task which is independent from the target cluster implementation (Openstack, ...). For example, an instance migration is a Meta-Action which corresponds, in the Openstack context, to a set of technical actions on the Nova, Cinder and Neutron components.

Using Meta-Actions instead of technical actions brings two advantages in Watcher :
* a loose coupling between the Watcher Decision Engine and the Watcher Applier
* a simplification of the optimization algorithms which don't need to know the underlying technical cluster implementation

Beyond that, the Meta-Actions which are computed by the optimization strategy are not necessarily ordered in time (it depends on the selected Strategy). Therefore, the Actions Planner module of Decision Engine reorganizes the list of Meta-Actions into an ordered sequence of technical actions (migrations, ...) such that all security, dependency, and performance requirements are met. An ordered sequence of technical actions is called an "Action Plan". 

The Decision Engine saves the generated Action Plan in the Watcher Database. This Action Plan is loaded later by the Watcher Actions Applier.

Like every Watcher component, the Decision Engine notifies its current status (learning phase, current status of each Audit, ...) on the message/notification bus. 

## Watcher Compute Node Profiler

This module of the Decision Engine is responsible for profiling a new compute node. When a new compute node is added to the cluster, it automatically triggers test scripts in order to extract profiling information such as :
* the maximum I/O available on each disk
* the evolution of energy consumption for a given workload 

It stores those information in the Watcher database. They may be used by any optimization strategy that needs to rely on real metrics about a given physical machine and not only theoretical metrics.

## Watcher Metrics Predictor

This module of the Decision Engine is able to compute some predicted metric values according to previously acquired metrics.

For instance, it may be able to predict the future CPU in the next 5 minutes for a given instance given the previous CPU load during the last 2 hours (relying on some neural network algorithm or any other machine learning system).

This component pushes the new predicted metrics to the CEP in order to trigger new actions if needed.

## Watcher Cluster State Collector

This module of the Decision Engine provides a high level API for requesting status information from the InfluxDb database.

A DSL will be provided in order to ease the development of new optimization strategies.

Example of high level requests that may be provided :
* get the difference between current cluster state and cluster state yesterday at the same time
* get the state evolution in time of a group of instances from 9 AM to 10 AM for every day of the week
* ... 

## Watcher Resource Metrics Collector

This module of the Decision Engine provides a high level API for requesting metrics information from the InfluxDb database.

A DSL will be provided in order to ease the development of new optimization strategies.

This component is distinct from the Cluster State Collector because it will probably have to deal with a much more important set of data and it may need a specific DSL for applying mathematical computes on metrics (min, max, average, ...).


## Watcher Actions Planner

This module of the Decision Engine translates Meta-Actions into technical actions on the Openstack modules (Nova, Cinder, ...) and builds an appropriate workflow which defines how-to schedule in time those different technical actions and for each action what are the pre-requisite conditions.

Today, the Action Plan is just a simple chain of sequential actions but in later versions, we intend to rely on more complex workflow models description formats, such as [BPMN 2.0](http://www.bpmn.org/), which enable a complete definition of activity diagrams containing sequential and parallel tasks.

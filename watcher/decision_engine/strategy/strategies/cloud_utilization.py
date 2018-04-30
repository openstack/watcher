import abc
import six
import socket
from watcher._i18n import _
from watcher.decision_engine.strategy.strategies import base
from watcher.common import exception as exc
from monascaclient import exc as exce
from watcher.datasource import monasca as mon
from watcher.decision_engine.model import element
from watcher.common import nova_helper


class CloudUtilization(base.CloudUtilizationBaseStrategy):

    def __init__(self, config, osc=None):
        super(CloudUtilization, self).__init__(config, osc)

        self._monasca = None

    @property
    def monasca(self):
        if self._monasca is None:
            self._monasca = mon.MonascaHelper(osc=self.osc)
        return self._monasca

    @monasca.setter
    def monasca(self,m):
        if self._monasca is None:
            self._monasca = m

    @classmethod
    def get_name(cls):
        return "cloud_utilization"

    @property
    def period(self):
        return self.input_parameters.get('period', 60)

    @property
    def threshold_level(self):
        return self.input_parameters.get('threshold_level', 20)

    @classmethod
    def get_display_name(cls):
        return _("Cloud Utilization")

    @classmethod
    def get_translatable_display_name(cls):
        return "Cloud Utilization"

    @classmethod
    def get_schema(cls):
        return {
            "properties": {
                "period": {
                    "description": "The time interval in seconds"
                                   "for getting statistic aggregation",
                    "type": "number",
                    "default": 60                 
                },
                "threshold_level":{
                    "description": "The Acceptable"
                                   "utilization level of cloud resources",
                    "type": "number",
                    "default": 50
            },
        },
    }
    METRIC_NAMES = dict(
        monasca=dict(
            host_cpu_usage='cpu.percent',
            host_ram_free='mem.usable_perc')
    )

    def get_node_cpu_usage(self,node):
        metric_name = self.METRIC_NAMES[
            'monasca']['host_cpu_usage']

        #pdb.set_trace()
        statistics = self.monasca.statistic_aggregation(
           meter_name = metric_name,
           dimensions = dict(hostname=node.uuid),
           period = self.period,
           aggregate = 'avg')
        #pdb.set_trace()
        if statistics:
            for stat in statistics:
                avg_col_idx = stat['columns'].index('avg')
                values = [r[avg_col_idx] for r in stat['statistics']]
                value = float(sum(values)) / len(values)
                cpu_usage = value
        else:
            cpu_usage = -1

        return cpu_usage

    def get_node_memory_usage(self,node):
        metric_name = self.METRIC_NAMES['monasca']['host_ram_free']

        statistics = self.monasca.statistic_aggregation(
           meter_name = metric_name,
           dimensions = dict(hostname=node.uuid),
           period = self.period,
           aggregate = 'avg')

        if statistics:
            for stat in statistics:
                avg_clo_idx = stat['columns'].index('avg')
                values = [100 - r[avg_clo_idx] for r in stat['statistics']]
                value = float(sum(values)) / len(values)
                memory_usage = value

        else:
            memory_usage = -1

        return memory_usage
            

    def calculate_score_node(self,node):
        """Calculate the score based on the 
        cpu utilization level"""

        host_avg_cpu_util = self.get_node_cpu_usage(node)
        host_avg_memory_util = self.get_node_memory_usage(node)

        #total_cores_used = nodes.vcpus * (host_avg_cpu_util / 100.0)
        return host_avg_cpu_util, host_avg_memory_util

     
    def pre_execute(self):
        #self.solution.add_action(action_type="nop",
        #                         input_parameters = parameters)

        cpu_utilization_cluster = []
        memory_utilization_cluster = []

        for node in self.compute_model.get_all_compute_nodes().values():
            cpu_result, memory_result = self.calculate_score_node(node)
            #pdb.set_trace()
            cpu_utilization_cluster.append(cpu_result)
            memory_utilization_cluster.append(memory_result)


        cpu_utilization_cluster = [v for v in cpu_utilization_cluster if v > 0]
        memory_utilization_cluster = [i for i in memory_utilization_cluster if i > 0]

        #pdb.set_trace()
        self.avg_cpu_utilization = sum(cpu_utilization_cluster) / len(cpu_utilization_cluster)
        self.avg_memory_utilization = sum(memory_utilization_cluster) / len(memory_utilization_cluster)
        print '************Collected cpu and memory statistics*********************'
        print self.avg_cpu_utilization, self.avg_memory_utilization
        
    def do_execute(self):
        if self.avg_cpu_utilization < self.threshold_level and self.avg_memory_utilization < self.threshold_level:
            print '*********Collected stats is less than threshold*****************'
            nova = nova_helper.NovaHelper()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host = '128.31.28.53'
            port = 9999
            s.connect((host,port))
            s.send('openstack_nodes')
            nodes = s.recv(1024)
            nodes_status = []

            #Get the status of the openstack node node in nodes.decode('ascii'):
            if 'False' not in nodes:
                for node in nodes.decode('ascii').split():
                #node = nodes[0]
                #pdb.set_trace()
                    s.send(node)
                    status = s.recv(1024)
                    #pdb.set_trace()
                    if status == 'SUSPEND':
                      try:
                        node_info = nova.get_instance_by_name(node)
                        node_id = node_info[0].id
                      except:
                        print "Unable to find the id"

                      try:
                        #Change the status of node to resume in openstack cluster and then in slurm cluster as well
                        response = nova.resume_instance(node_id)
                      except:
                        print "Unable to resume the instance in the openstack cluster"
                    
                      try:
                        parameter = 'resume'+node
                        s.send(parameter)
                        #s.send(node)
                        resp = s.recv(1024)
                        s.send(node)
                        res = s.recv(1024)

                        if 'IDLE' in res:
                            nodes_status.append(res)

                      except:
                        print "Unable to resume the instance in the slurm cluster"
                
                    else:
                      nodes_status.append(status)
            
            #Look for the jobs
            node_status = []
            if 'SUSPENDED' not in nodes_status:
                s.send('jobs')
                job = s.recv(1024).decode('ascii')

                #Create an instance as a jo
                if job == 'True':
                    try:
                        s.send('spawn_instance')
                    except:
                        print 'Unable to create an instance'
           
            s.close()

        elif self.avg_cpu_utilization > self.threshold_level or self.avg_memory_utilization > self.threshold_level:
            print '*********Collected stats is more than threshold*****************'
            nova = nova_helper.NovaHelper()
            #pdb.set_trace()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host = '128.31.28.53'
            port = 9999
            s.connect((host,port))
            s.send('openstack_nodes')
            nodes = s.recv(1024)
            nodes = nodes.split() 
            #s.close()

            for node in nodes:
                #s.connect((host,port))
                s.send(node)
                status = s.recv(1024)
                #s.close()
                if status.decode('ascii') == 'IDLE' or 'RUNNING':
                    try:
                        #pdb.set_trace()
                        node_info = nova.get_instance_by_name(node)
                        node_id = node_info[0].id
                    except:
                        print "Unable to find the id"

                    #Suspend the node in the slurm cluster and then in openstack cluster as well
                    try:
                        #s.connect((host,port))
                        parameter = 'suspend'+node
                        s.send(parameter)
                        s.send(node)
                        resp = s.recv(1024)
                        if resp:
                            response = nova.suspend_instance(node_id)
                        #s.close()
                    except:
                        print 'Unable to suspend the node'
            s.close()            


    def post_execute(self):
        self.solution.add_action(action_type="nop")
        return self.solution

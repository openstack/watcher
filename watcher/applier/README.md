# Watcher Actions Applier

This component is in charge of executing the plan of actions built by the Watcher Actions Planner.

For each action of the workflow, this component may call directly the component responsible for this kind of action (Example : Nova API for an instance migration) or via some publish/subscribe pattern on the message bus.

It notifies continuously of the current progress of the Action Plan (and atomic Actions), sending status messages on the bus. Those events may be used by the CEP to trigger new actions.

This component is also connected to the Watcher MySQL database in order to:
* get the description of the action plan to execute
* persist its current state so that if it is restarted, it can restore each Action plan context and restart from the last known safe point of each ongoing workflow.

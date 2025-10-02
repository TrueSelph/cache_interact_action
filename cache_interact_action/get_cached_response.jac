import from jivas.agent.core.agent { Agent }
import from jivas.agent.action.action { Action }
import from jivas.agent.action.actions { Actions }
import from jivas.agent.modules.action.path { action_walker_path }
import from jivas.agent.action.agent_graph_walker { agent_graph_walker }


walker get_cached_response(agent_graph_walker) {

    has score_threshold:float = 0.0;
    has query:str = "";
    has filter:str = "";
    has response:dict = {};
    has reporting:bool = True;

    class __specs__ {
        static has private: bool = False;
        static has path: str = action_walker_path(__module__);
    }

    can on_agent with Agent entry {
        visit [-->](`?Actions);
    }

    can on_actions with Actions entry {
        visit [-->](`?Action)(?enabled==True)(?label=='CacheInteractAction');
    }

    can on_action with Action entry {
        self.response = here.retrieve_context(
            query=self.query,
            filter=self.filter,
            score_threshold=self.score_threshold
        );

        if self.reporting {
            report self.response;
        }

    }

}
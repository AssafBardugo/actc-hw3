from controllers.base import Controller
from actual_state.types import ResourceType
from actual_state.resources import Resource
from actual_state.store import ResourceStore
from api_runtime.validate_resource import validate_pod


class ReplicaSetController(Controller):

    def __init__(self, store: ResourceStore) -> None:
        self.store = store


    def reconcile(self) -> None:
        all_replica_sets = self.store.list_by_kind(ResourceType.REPLICASET)

        for namespace, replica_sets in all_replica_sets.items():

            for rs in replica_sets.values():

                # Only Pods explicitly owned by this ReplicaSet are considered.
                # Pods matching the selector but not owned are intentionally ignored
                # to prevent interference between ReplicaSets.

                for i in range(rs.spec["replicas"]):

                    pod_name = f"own_by_{rs.name}_{i}"

                    if not self.store.get(ResourceType.POD, pod_name, namespace):
                        body = {
                            "kind": "Pod",
                            "metadata": {
                                "name": pod_name,
                                "labels": rs.spec["template"]["metadata"]["labels"]
                            },
                            "spec": rs.spec["template"]["spec"]
                        }
                        pod = validate_pod(namespace, body)
                        self.store.create(pod)

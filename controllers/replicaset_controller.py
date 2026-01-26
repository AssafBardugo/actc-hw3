from controllers.base import Controller
from actual_state.types import ResourceType
from actual_state.resources import Resource
from actual_state.store import ResourceStore


class ReplicaSetController(Controller):

    def __init__(self, store: ResourceStore) -> None:
        self.store = store


    def reconcile(self) -> None:
        all_replica_sets = self.store.list_by_kind(ResourceType.REPLICASET)

        for namespace, replica_sets in all_replica_sets.items():

            pods_in_ns = self.store.list_by_namespace_and_kind(ResourceType.POD, namespace)

            for rs in replica_sets.values():
                self._reconcile_single_replicaset(rs, pods_in_ns)


    def _reconcile_single_replicaset(self, replica_set: Resource, pods_in_namespace: dict[str, Resource]) -> None:
        if replica_set.spec is None:
            return

        if "replicas" not in replica_set.spec:
            return

        desired_replicas = replica_set.spec["replicas"]

        # Only Pods explicitly owned by this ReplicaSet are considered.
        # Pods matching the selector but not owned are intentionally ignored
        # to prevent interference between ReplicaSets.
        owned_pods: list[Resource] = []

        for pod in pods_in_namespace.values():
            if pod.metadata is None:
                continue

            owner = pod.metadata.get("owner")
            if owner is None:
                continue

            if owner.get("kind") != "replicaset":
                continue

            if owner.get("name") != replica_set.name:
                continue

            owned_pods.append(pod)

        current = len(owned_pods)

        if current < desired_replicas:
            to_create = desired_replicas - current
            for i in range(to_create):
                self._create_pod(replica_set, i)

        elif current > desired_replicas:
            to_delete = current - desired_replicas
            for pod in owned_pods[:to_delete]:
                self.store.delete(
                    kind=ResourceType.POD,
                    name=pod.name,
                    namespace=pod.namespace,
                )


    def _create_pod(self, replica_set: Resource, index: int) -> None:
        rs_name = replica_set.metadata.get("name")
        namespace = replica_set.metadata.get("namespace", "default")

        pod_name = f"{rs_name}-pod-{id(replica_set)}-{index}"

        template = replica_set.spec.get("template", {})
        labels = template.get("labels", {})

        pod = Resource(
            kind=ResourceType.POD,
            name=pod_name,
            namespace=namespace,
            metadata={
                "labels": labels,
                "owner": {
                    "kind": "replicaset",
                    "name": rs_name,
                },
            },
            spec=template.get("spec", {}),
        )

        self.store.create(pod)

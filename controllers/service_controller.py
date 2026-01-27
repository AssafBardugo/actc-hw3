from controllers.base import Controller
from actual_state.types import ResourceType
from actual_state.store import ResourceStore
from api_runtime.podman import PodmanRuntime


class ServiceController(Controller):
    store: ResourceStore

    def __init__(self, store: ResourceStore, runtime: PodmanRuntime) -> None:
        self.store = store
        self.desired_state = runtime


    def reconcile(self) -> None:
        all_services = self.store.list_by_kind(ResourceType.SERVICE)

        for namespace, services in all_services.items():

            pods_in_ns = self.store.list_by_namespace_and_kind(ResourceType.POD, namespace)

            for service in services.values():

                if service.spec["selector"] == {}:
                    continue

                matched_pods = []
                for pod in pods_in_ns.values():

                    if all(pod.metadata["labels"].get(k) == v for k, v in service.spec["selector"].items()):
                        matched_pods.append(pod.name)
                
                if not matched_pods:
                    print(f'Warning: Service {service.name} with the selector {service.spec["selector"]} matches no pods')
                
                self.desired_state.services_endpoints[(service.namespace, service.name)] = set(matched_pods)

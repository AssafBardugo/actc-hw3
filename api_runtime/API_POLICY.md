# API_POLICY.md

Notes about how the API is supposed to behave in this project.
This file exists so that decisions about required fields, defaults, and validation are written down in one place.

The goal is to be consistent and simple, not to fully match Kubernetes.

---

General ideas:

* Validation happens in the API layer, not inside the Resource class
* Resource objects are just data holders
* If we cannot know what to run -> return HTTP 400
* If a field is only metadata -> allow it to be missing

---

POD

Required:

* apiVersion
* kind = Pod
* metadata.name
* metadata.namespace (default = "default")
* spec
* spec.containers
* exactly one container
* container.image

Optional:

* metadata.labels
* container.env

Rejected (HTTP 400):

* missing spec
* missing containers
* containers is not a list
* more than one container
* container without image

Defaults / behavior:

* If container name is missing, a default name may be assigned
* If labels are missing, pod belongs to no Service and no ReplicaSet


---

SERVICE

Required:

* apiVersion
* kind = Service
* metadata.name
* metadata.namespace (default = "default")
* spec
* spec.ports
* spec.ports[0].port

Optional:

* metadata.labels
* spec.type (default = ClusterIP)
* spec.ports[0].targetPort (default = port)
* spec.ports[0].protocol (assume TCP)

Rejected (HTTP 400):

* missing spec
* missing ports

Special case:

* if "selector" is not in spec, we accept it. but the service will be unusable.
* Empty selector {} is allowed, but service has no endpoints


---

REPLICASET

A ReplicaSet ensures that a certain number of pods exist.

Required:

* apiVersion
* kind = ReplicaSet
* metadata.name
* metadata.namespace (default = "default")
* spec.replicas
* spec.selector
* spec.template
* spec.template.spec.containers
* exactly one container in template
* template container.image

Optional:

* metadata.labels
* template container.env

Rejected (HTTP 400):

* missing spec
* missing replicas
* missing selector
* missing template
* missing template containers
* more than one container in template

Defaults:

* spec.template.metadata.labels is default to be spec.selector


---

ERROR CODES

* Missing or invalid required field -> 400
* Resource already exists -> 409
* Resource not found -> 404

---


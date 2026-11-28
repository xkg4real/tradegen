"""Whitelisted component registry replacing arbitrary importlib.import_module."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from qlib_lab.exceptions import SecurityRefusalError

# Maps registered component class name -> (class_obj, category, allowed_module_prefixes)
COMPONENT_REGISTRY: dict[str, tuple[type, str]] = {}

_ALLOWED_MODULE_PREFIXES = (
    "qlib_lab.",
    "qlib_lab",
)


def register_component(category: str, name: str | None = None):
    """Decorator to register a trusted qlib_lab component class in COMPONENT_REGISTRY."""
    if not isinstance(category, str) or not category.strip():
        raise ValueError("category must be a non-empty string")

    def _decorator(cls: type) -> type:
        comp_name = name or cls.__name__
        existing = COMPONENT_REGISTRY.get(comp_name)
        if existing is not None and existing[0] is not cls:
            raise SecurityRefusalError(
                f"Component {comp_name!r} already bound to {existing[0].__qualname__}"
            )
        COMPONENT_REGISTRY[comp_name] = (cls, category)
        return cls

    return _decorator


_BOOTSTRAPPED = False


def _ensure_all_registered() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    _BOOTSTRAPPED = True
    import qlib_lab.data  # noqa: F401
    import qlib_lab.models  # noqa: F401
    import qlib_lab.online  # noqa: F401
    import qlib_lab.workflow  # noqa: F401


def get_registered_class(name: str, *, category: str | None = None) -> type:
    """Resolve a whitelisted class by name without dynamic module importing."""
    _ensure_all_registered()
    if not isinstance(name, str) or not name.strip():
        raise SecurityRefusalError(f"Invalid component class name: {name!r}")
    entry = COMPONENT_REGISTRY.get(name)
    if entry is None:
        raise SecurityRefusalError(
            f"Component {name!r} is not in COMPONENT_REGISTRY; arbitrary class loading is refused"
        )
    cls, reg_category = entry
    if category is not None and reg_category != category:
        raise SecurityRefusalError(
            f"Component {name!r} belongs to category {reg_category!r}, expected {category!r}"
        )
    return cls


def init_instance_by_config(
    config: Any,
    accept_types: type | tuple[type, ...] | None = None,
    *,
    category: str | None = None,
    extra_kwargs: Mapping[str, Any] | None = None,
) -> Any:
    """Instantiate a component strictly from COMPONENT_REGISTRY or validate an existing instance.

    Never calls importlib.import_module, getattr on arbitrary modules, or dynamic code execution.
    """
    if accept_types is not None and isinstance(config, accept_types) and not isinstance(config, (str, Mapping)):
        return config

    if isinstance(config, str):
        cls_name = config
        kwargs: dict[str, Any] = {}
        module_path = None
    elif isinstance(config, Mapping):
        if "class" not in config:
            raise SecurityRefusalError("Component config dict must contain a 'class' key")
        cls_name = config["class"]
        module_path = config.get("module_path")
        raw_kwargs = config.get("kwargs", {})
        if raw_kwargs is None:
            kwargs = {}
        elif isinstance(raw_kwargs, Mapping):
            kwargs = dict(raw_kwargs)
        else:
            raise SecurityRefusalError(f"Component 'kwargs' for {cls_name!r} must be a mapping")
        unknown_top = set(config.keys()) - {"class", "kwargs", "module_path"}
        if unknown_top:
            # Allow flat kwargs style only if explicitly clean? Refuse unknown top-level keys to fail closed.
            raise SecurityRefusalError(
                f"Component config for {cls_name!r} has unexpected top-level keys {sorted(unknown_top)}"
            )
    else:
        if accept_types is None and hasattr(config, "__class__") and config.__class__.__name__ in COMPONENT_REGISTRY:
            return config
        raise SecurityRefusalError(f"Unsupported component configuration type: {type(config).__name__}")

    if module_path is not None:
        if not isinstance(module_path, str) or not module_path.startswith(_ALLOWED_MODULE_PREFIXES):
            raise SecurityRefusalError(
                f"Disallowed module_path {module_path!r} for {cls_name!r}; external module loading is refused"
            )

    cls = get_registered_class(cls_name, category=category)
    if module_path is not None and not cls.__module__.startswith(module_path):
        # Allow parent package module_path (e.g. "qlib_lab.models" for "qlib_lab.models.gbdt")
        if cls.__module__ != module_path and not cls.__module__.startswith(module_path + "."):
            raise SecurityRefusalError(
                f"Component {cls_name!r} lives in {cls.__module__!r}, mismatching declared {module_path!r}"
            )

    merged_kwargs = dict(kwargs)
    if extra_kwargs:
        merged_kwargs.update(extra_kwargs)

    instance = cls(**merged_kwargs)
    if accept_types is not None and not isinstance(instance, accept_types):
        raise SecurityRefusalError(
            f"Instantiated {cls_name!r} ({type(instance).__name__}) is not an instance of {accept_types}"
        )
    return instance


def list_registered_components() -> dict[str, str]:
    """Return {class_name: category} snapshot of all whitelisted components."""
    _ensure_all_registered()
    return {name: cat for name, (_cls, cat) in sorted(COMPONENT_REGISTRY.items())}

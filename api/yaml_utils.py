"""Safe YAML parsing with optional libyaml acceleration."""
import yaml


def safe_load(text):
    """Preserve SafeLoader customizations and never accept Python object tags."""
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    # The C and Python loaders have separate registries. Respect extensions
    # that register constructors or resolvers on the public SafeLoader.
    if any(getattr(loader, name) != getattr(yaml.SafeLoader, name) for name in (
        "yaml_constructors", "yaml_multi_constructors", "yaml_implicit_resolvers",
        "yaml_path_resolvers",
    )):
        loader = yaml.SafeLoader
    return yaml.load(text, Loader=loader)

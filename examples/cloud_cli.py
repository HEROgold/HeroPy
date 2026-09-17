"""A fictional multi-cloud CLI: ten levels deep, with 1-5 sibling subcommands per level.

Only one branch actually runs ten levels deep (compute -> instances -> create ->
from-image -> with-disk -> attach -> ssd -> rule -> add -> port/cidr/tag); the other
siblings at each level are leaves, the way a real CLI's command tree tends to look.
"""

from __future__ import annotations

from herogold.argparse import Actions, Argument, Namespace, entrypoint


class CloudCli(Namespace):
    """cloudctl - manage compute, storage, network, database, and monitoring resources."""

    region = Argument("region", help="Target cloud region", default="us-east-1")
    output = Argument("output", help="Output format (table, json, yaml)", default="table")


# Level 1 - resource domains (5 siblings)
class Compute(CloudCli, subcommand="compute"):
    """Manage compute resources."""


class Storage(CloudCli, subcommand="storage"):
    """Manage storage resources."""

    bucket_prefix = Argument("bucket_prefix", help="Default bucket name prefix", default="app")


class Network(CloudCli, subcommand="network"):
    """Manage network resources."""


class Database(CloudCli, subcommand="database"):
    """Manage managed database instances."""

    engine = Argument("engine", help="Database engine", default="postgres")


class Monitoring(CloudCli, subcommand="monitoring"):
    """Query monitoring and alerting."""

    window = Argument("window", help="Lookback window, e.g. 1h or 24h", default="1h")


# Level 2 - compute sub-resources (3 siblings)
class Instances(Compute, subcommand="instances"):
    """Manage compute instances."""


class Images(Compute, subcommand="images"):
    """Manage machine images."""

    owner = Argument("owner", help="Filter images by owner account", default="self")


class Snapshots(Compute, subcommand="snapshots"):
    """Manage disk snapshots."""


# Level 3 - instance actions (4 siblings)
class InstancesList(Instances, subcommand="list"):
    """List instances."""

    limit = Argument("limit", type_=int, help="Maximum number of results", default=20)
    status = Argument("status", help="Filter by instance status", default="running")


class InstancesDelete(Instances, subcommand="delete"):
    """Delete an instance."""

    instance_id = Argument("instance_id", help="Instance ID to delete", default="")
    force = Argument("force", action=Actions.STORE_BOOL, help="Skip the confirmation prompt", default=False)


class InstancesResize(Instances, subcommand="resize"):
    """Resize an instance."""

    instance_id = Argument("instance_id", help="Instance ID to resize", default="")
    size = Argument("size", help="New instance size", default="medium")


class InstancesCreate(Instances, subcommand="create"):
    """Create a new instance."""

    name = Argument("name", help="Name for the new instance", default="")


# Level 4 - creation source (2 siblings)
class CreateFromSnapshot(InstancesCreate, subcommand="from-snapshot"):
    """Create an instance from an existing snapshot."""

    snapshot_id = Argument("snapshot_id", help="Source snapshot ID", default="")


class CreateFromImage(InstancesCreate, subcommand="from-image"):
    """Create an instance from a machine image."""

    image_id = Argument("image_id", help="Source image ID", default="")


# Level 5 - extra configuration (3 siblings)
class ImageMinimal(CreateFromImage, subcommand="minimal"):
    """Create with no extra configuration."""


class ImageWithNetwork(CreateFromImage, subcommand="with-network"):
    """Create and attach to an existing network."""

    subnet = Argument("subnet", help="Subnet to place the instance in", default="default")


class ImageWithDisk(CreateFromImage, subcommand="with-disk"):
    """Create with an additional data disk, then configure it."""


# Level 6 - disk action (2 siblings)
class DiskReference(ImageWithDisk, subcommand="reference"):
    """Reference an existing disk instead of attaching a new one."""

    disk_id = Argument("disk_id", help="Existing disk ID to reference", default="")


class DiskAttach(ImageWithDisk, subcommand="attach"):
    """Attach a new data disk to the instance."""


# Level 7 - disk type (4 siblings)
class DiskHdd(DiskAttach, subcommand="hdd"):
    """Attach a standard HDD-backed disk."""

    size_gb = Argument("size_gb", type_=int, help="Disk size in GB", default=100)


class DiskNvme(DiskAttach, subcommand="nvme"):
    """Attach a high-throughput NVMe disk."""

    size_gb = Argument("size_gb", type_=int, help="Disk size in GB", default=250)


class DiskEphemeral(DiskAttach, subcommand="ephemeral"):
    """Attach local ephemeral storage."""


class DiskSsd(DiskAttach, subcommand="ssd"):
    """Attach an SSD-backed disk, then configure its firewall rule."""

    size_gb = Argument("size_gb", type_=int, help="Disk size in GB", default=100)


# Level 8 - firewall (2 siblings)
class FirewallSkip(DiskSsd, subcommand="skip"):
    """Skip firewall configuration."""


class FirewallRule(DiskSsd, subcommand="rule"):
    """Attach a firewall rule to the instance, then add match conditions."""

    rule_name = Argument("rule_name", help="Firewall rule name", default="default-allow")


# Level 9 - rule condition (2 siblings)
class RuleClear(FirewallRule, subcommand="clear"):
    """Clear all match conditions on the rule."""


class RuleAdd(FirewallRule, subcommand="add"):
    """Add a match condition to the rule."""


# Level 10 - condition value (3 siblings)
class ConditionPort(RuleAdd, subcommand="port"):
    """Match on a destination port."""

    port = Argument("port", type_=int, help="Destination port", default=443)


class ConditionCidr(RuleAdd, subcommand="cidr"):
    """Match on a source CIDR block."""

    cidr = Argument("cidr", help="Source CIDR block", default="0.0.0.0/0")


class ConditionTag(RuleAdd, subcommand="tag"):
    """Match on an instance tag."""

    tag = Argument("tag", help="Tag key=value to match", default="env=prod")


@entrypoint(CloudCli)
def main(options: CloudCli) -> None:
    resolved = type(options)
    print("Resolved command:", _command_path(resolved))

    seen: set[str] = set()
    for klass in resolved.__mro__:
        for name, value in vars(klass).items():
            if isinstance(value, Argument) and name not in seen:
                seen.add(name)
                print(f"  {name} = {getattr(options, name)!r}")


def _command_path(cls: type[CloudCli]) -> str:
    """Reconstruct the dotted subcommand chain for `cls`, e.g. compute.instances.create."""
    names: list[str] = []
    node = cls
    while node is not CloudCli:
        names.append(node.__name__)
        node = node.__bases__[0]
    return " -> ".join(reversed(names)) or cls.__name__


if __name__ == "__main__":
    main()

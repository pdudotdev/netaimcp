from pydantic import BaseModel, Field

# OSPF query - input model
class OspfQuery(BaseModel):
    device: str = Field(..., description="Device name from inventory")
    query: str = Field(..., description="neighbors | database | borders | config | interfaces | details")

# EIGRP query - input model
class EigrpQuery(BaseModel):
    device: str = Field(..., description="Device name from inventory")
    query: str = Field(..., description="neighbors | topology | config | interfaces")

# BGP query - input model
class BgpQuery(BaseModel):
    device: str
    query: str = Field(..., description="summary | detail | config")

class RoutingQuery(BaseModel):
    device: str
    prefix: str | None = Field(None, description="Optional prefix to look up")

# Routing policies query - input model
class RoutingPolicyQuery(BaseModel):
    device: str
    query: str = Field(..., description="route_maps | prefix_lists | policy_based_routing | access_lists")

# Interfaces query - input model
class InterfacesQuery(BaseModel):
    device: str = Field(..., description="Device name from inventory")

# Ping - input model
class PingInput(BaseModel):
    device: str = Field(..., description="Device name from inventory")
    destination: str = Field(..., description="IP address to ping")
    source: str | None = Field(None, description="Optional source IP or interface")

# Traceroute - input model
class TracerouteInput(BaseModel):
    device: str = Field(..., description="Device name from inventory")
    destination: str = Field(..., description="IP address to trace")

# Show command - input model
class ShowCommand(BaseModel):
    """Run a show command against a network device."""
    device: str = Field(..., description="Device name from inventory (e.g. R1, R2, R3)")
    command: str = Field(..., description="Show command to execute on the device")

# Config commands - input model
class ConfigCommand(BaseModel):
    """Send configuration commands to one or more devices."""
    devices: list[str] = Field(..., description="Device names from inventory (e.g. ['R1','R2','R3'])")
    commands: list[str] = Field(..., description="Configuration commands to apply")

# Empty placeholder - input model
class EmptyInput(BaseModel):
    pass

# Snapshot - input model
class SnapshotInput(BaseModel):
    devices: list[str] = Field(..., description="Devices to snapshot (e.g. R1, R2, R3)")
    profile: str = Field(..., description="Snapshot profile (e.g. ospf, stp)")

# Risk score - input model
class RiskInput(BaseModel):
    devices: list[str] = Field(..., description="Devices affected by the config change")
    commands: list[str] = Field(..., description="The configuration commands to apply")
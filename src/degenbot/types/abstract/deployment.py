from dataclasses import dataclass

from degenbot.types_solver.aliases import ChainId


@dataclass(slots=True, frozen=True)
class AbstractExchangeDeployment:
    name: str
    chain_id: ChainId

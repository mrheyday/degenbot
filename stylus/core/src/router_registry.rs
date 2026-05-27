use alloy_primitives::address;
use stylus_sdk::alloy_primitives::Address;

pub const UNIV2_ROUTER: Address = address!("4752ba5DBc23f44D87826276BF6Fd6b1C372aD24");
pub const UNIV2_FACTORY: Address = address!("f1D7CC64Fb4452F05c498126312eBE29f30Fbcf9");
pub const UNIV3_FACTORY: Address = address!("1F98431c8aD98523631AE4a59f267346ea31F984");
pub const UNIV3_POSITION_MANAGER: Address = address!("C36442b4a4522E871399CD717aBDD847Ab11FE88");
pub const UNIV3_SWAP_ROUTER_02: Address = address!("68b3465833fb72A70ecDF485E0e4C7bD8665Fc45");
pub const UNIV3_QUOTER_V2: Address = address!("61fFE014bA17989E743c5F6cB21bF9697530B21e");
pub const UNIV4_POOL_MANAGER: Address = address!("360E68faCcca8cA495c1B759Fd9EEe466db9FB32");
pub const UNIV4_POSITION_MANAGER: Address = address!("d88F38F930b7952f2DB2432Cb002E7abbF3dD869");
pub const UNIV4_STATE_VIEW: Address = address!("76Fd297e2D437cd7f76d50F01AfE6160f86e9990");
pub const UNIV4_QUOTER: Address = address!("3972C00f7ed4885e145823eb7C655375d275A1C5");
pub const UNIVERSAL_ROUTER_V20: Address = address!("A51afAFe0263b40EdaEf0Df8781eA9aa03E381a3");
pub const UNIVERSAL_ROUTER_V211: Address = address!("8B844f885672f333Bc0042cB669255f93a4C1E6b");
pub const UNIVERSAL_ROUTER_LEGACY: Address = UNIVERSAL_ROUTER_V20;
pub const UNIVERSAL_ROUTER_LATEST: Address = UNIVERSAL_ROUTER_V211;
pub const UNISWAPX_V3_DUTCH_REACTOR: Address = address!("B274d5F4b833b61B340b654d600A864fB604a87c");
pub const UNISWAPX_ORDER_QUOTER: Address = address!("88440407634F89873c5D9439987Ac4BE9725fea8");
pub const SQUID_ROUTER: Address = address!("ce16F69375520ab01377ce7B88f5BA8C48F8D666");
pub const SQUID_MULTICALL: Address = address!("aD6Cea45f98444a922a2b4fE96b8C90F0862D2F4");
pub const PERMIT2: Address = address!("000000000022D473030F116dDEE9F6B43aC78BA3");
pub const SUSHI_V2_FACTORY: Address = address!("c35DADB65012eC5796536bD9864eD8773aBc74C4");
pub const SUSHI_V2_ROUTER: Address = address!("1b02dA8Cb0d097eB8D57A175b88c7D8b47997506");
pub const PANCAKE_V2_FACTORY: Address = address!("02a84c1b3BBD7401a5f7fa98a384EBC70bB5749E");
pub const PANCAKE_V2_ROUTER: Address = address!("8cFe327CEc66d1C090Dd72bd0FF11d690C33a2Eb");
pub const CAMELOT_V2_FACTORY: Address = address!("6EcCab422D763aC031210895C81787E87B43A652");
pub const FRAXSWAP_FACTORY: Address = address!("5Ca135cB8527d76e932f34B5145575F9d8cbE08E");
pub const SUSHI_V3_FACTORY: Address = address!("1af415a1EbA07a4986a52B6f2e7dE7003D82231e");
pub const SUSHI_V3_SWAP_ROUTER: Address = address!("8A21F6768C1f8075791D08546Dadf6daA0bE820c");
pub const PANCAKE_V3_SMART_ROUTER: Address = address!("32226588378236Fd0c7c4053999F88aC0e5cAc77");
pub const CAMELOT_V3_SWAP_ROUTER: Address = address!("1F721E2E82F6676FCE4eA07A5958cF098D339e18");

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum RouterKind {
    UniversalRouterV20 = 0,
    UniversalRouterV211 = 1,
    Univ2Router = 2,
    Univ3SwapRouter02 = 3,
    Univ3PositionManager = 4,
    Univ4PoolManager = 5,
    Univ4PositionManager = 6,
    UniswapXV3DutchReactor = 7,
    CamelotV3SwapRouter = 8,
    PancakeV3SmartRouter = 9,
    SushiV2Router = 10,
    SushiV3SwapRouter = 11,
    SquidRouter = 12,
    PancakeV2Router = 13,
}

impl RouterKind {
    pub fn from_u8(value: u8) -> Option<Self> {
        match value {
            0 => Some(Self::UniversalRouterV20),
            1 => Some(Self::UniversalRouterV211),
            2 => Some(Self::Univ2Router),
            3 => Some(Self::Univ3SwapRouter02),
            4 => Some(Self::Univ3PositionManager),
            5 => Some(Self::Univ4PoolManager),
            6 => Some(Self::Univ4PositionManager),
            7 => Some(Self::UniswapXV3DutchReactor),
            8 => Some(Self::CamelotV3SwapRouter),
            9 => Some(Self::PancakeV3SmartRouter),
            10 => Some(Self::SushiV2Router),
            11 => Some(Self::SushiV3SwapRouter),
            12 => Some(Self::SquidRouter),
            13 => Some(Self::PancakeV2Router),
            _ => None,
        }
    }
}

pub fn router_for(kind: RouterKind) -> Address {
    match kind {
        RouterKind::UniversalRouterV20 => UNIVERSAL_ROUTER_V20,
        RouterKind::UniversalRouterV211 => UNIVERSAL_ROUTER_V211,
        RouterKind::Univ2Router => UNIV2_ROUTER,
        RouterKind::Univ3SwapRouter02 => UNIV3_SWAP_ROUTER_02,
        RouterKind::Univ3PositionManager => UNIV3_POSITION_MANAGER,
        RouterKind::Univ4PoolManager => UNIV4_POOL_MANAGER,
        RouterKind::Univ4PositionManager => UNIV4_POSITION_MANAGER,
        RouterKind::UniswapXV3DutchReactor => UNISWAPX_V3_DUTCH_REACTOR,
        RouterKind::CamelotV3SwapRouter => CAMELOT_V3_SWAP_ROUTER,
        RouterKind::PancakeV3SmartRouter => PANCAKE_V3_SMART_ROUTER,
        RouterKind::SushiV2Router => SUSHI_V2_ROUTER,
        RouterKind::SushiV3SwapRouter => SUSHI_V3_SWAP_ROUTER,
        RouterKind::SquidRouter => SQUID_ROUTER,
        RouterKind::PancakeV2Router => PANCAKE_V2_ROUTER,
    }
}

pub fn is_known(addr: Address) -> bool {
    matches!(
        addr,
        UNIVERSAL_ROUTER_V20
            | UNIVERSAL_ROUTER_V211
            | UNIV2_ROUTER
            | UNIV2_FACTORY
            | UNIV3_SWAP_ROUTER_02
            | UNIV3_POSITION_MANAGER
            | UNIV3_FACTORY
            | UNIV3_QUOTER_V2
            | UNIV4_POOL_MANAGER
            | UNIV4_POSITION_MANAGER
            | UNIV4_STATE_VIEW
            | UNIV4_QUOTER
            | UNISWAPX_V3_DUTCH_REACTOR
            | UNISWAPX_ORDER_QUOTER
            | PERMIT2
            | SUSHI_V2_ROUTER
            | SUSHI_V2_FACTORY
            | PANCAKE_V2_ROUTER
            | PANCAKE_V2_FACTORY
            | SUSHI_V3_SWAP_ROUTER
            | SUSHI_V3_FACTORY
            | CAMELOT_V2_FACTORY
            | CAMELOT_V3_SWAP_ROUTER
            | PANCAKE_V3_SMART_ROUTER
            | SQUID_ROUTER
            | SQUID_MULTICALL
            | FRAXSWAP_FACTORY
    )
}

pub mod commands {
    pub const V3_SWAP_EXACT_IN: u8 = 0x00;
    pub const V3_SWAP_EXACT_OUT: u8 = 0x01;
    pub const V2_SWAP_EXACT_IN: u8 = 0x08;
    pub const V2_SWAP_EXACT_OUT: u8 = 0x09;
    pub const WRAP_ETH: u8 = 0x0b;
    pub const UNWRAP_WETH: u8 = 0x0c;
    pub const V4_SWAP: u8 = 0x10;
    pub const EXECUTE_SUB_PLAN: u8 = 0x21;

    pub fn command_for(kind: u8) -> Option<u8> {
        match kind {
            0 => Some(V3_SWAP_EXACT_IN),
            1 => Some(V3_SWAP_EXACT_OUT),
            2 => Some(V2_SWAP_EXACT_IN),
            3 => Some(V2_SWAP_EXACT_OUT),
            4 => Some(WRAP_ETH),
            5 => Some(UNWRAP_WETH),
            6 => Some(V4_SWAP),
            7 => Some(EXECUTE_SUB_PLAN),
            _ => None,
        }
    }
}

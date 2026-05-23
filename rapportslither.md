'forge clean' running (wd: /Volumes/PNYRP60PSSD/dev-projects/mev-arbitrum/vendor/degenbot)
'forge config --json' running
'forge build --build-info contract_reference/aave/Pool/rev11.sol' running (wd: /Volumes/PNYRP60PSSD/dev-projects/mev-arbitrum/vendor/degenbot)

Detector: incorrect-equality
MathUtils.calculateCompoundedInterest(uint256,uint40,uint256) (contract_reference/aave/Pool/rev11.sol#3396-3431) uses a dangerous strict equality:
	- exp == 0 (contract_reference/aave/Pool/rev11.sol#3404)
ReserveLogic.getNormalizedDebt(DataTypes.ReserveData) (contract_reference/aave/Pool/rev11.sol#6882-6893) uses a dangerous strict equality:
	- timestamp == block.timestamp (contract_reference/aave/Pool/rev11.sol#6886)
ReserveLogic.getNormalizedIncome(DataTypes.ReserveData) (contract_reference/aave/Pool/rev11.sol#6861-6873) uses a dangerous strict equality:
	- timestamp == block.timestamp (contract_reference/aave/Pool/rev11.sol#6865)
ReserveLogic.updateState(DataTypes.ReserveData,DataTypes.ReserveCache) (contract_reference/aave/Pool/rev11.sol#6900-6913) uses a dangerous strict equality:
	- reserveCache.reserveLastUpdateTimestamp == uint40(block.timestamp) (contract_reference/aave/Pool/rev11.sol#6903)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#dangerous-strict-equalities

Detector: uninitialized-local
FlashLoanLogic.executeFlashLoan(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.UserConfigurationMap,DataTypes.FlashloanParams).vars (contract_reference/aave/Pool/rev11.sol#8079) is a local variable never initialized
ValidationLogic.validateBorrow(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.ValidateBorrowParams).vars (contract_reference/aave/Pool/rev11.sol#4004) is a local variable never initialized
LiquidationLogic._calculateAvailableCollateralToLiquidate(DataTypes.ReserveConfigurationMap,uint256,uint256,uint256,uint256,uint256,uint256,uint256).vars (contract_reference/aave/Pool/rev11.sol#5527) is a local variable never initialized
ReserveLogic.cache(DataTypes.ReserveData).reserveCache (contract_reference/aave/Pool/rev11.sol#7053) is a local variable never initialized
ValidationLogic.validateLiquidationCall(DataTypes.UserConfigurationMap,DataTypes.ReserveData,DataTypes.ReserveData,DataTypes.ValidateLiquidationCallParams).vars (contract_reference/aave/Pool/rev11.sol#4161) is a local variable never initialized
LiquidationLogic.executeLiquidationCall(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(address => DataTypes.UserConfigurationMap),mapping(uint8 => DataTypes.EModeCategory),DataTypes.ExecuteLiquidationCallParams).vars (contract_reference/aave/Pool/rev11.sol#5177) is a local variable never initialized
GenericLogic.calculateUserAccountData(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.CalculateUserAccountDataParams).vars (contract_reference/aave/Pool/rev11.sol#2377) is a local variable never initialized
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#uninitialized-local-variables

Detector: unused-return
BorrowLogic.executeRepay(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.UserConfigurationMap,DataTypes.ExecuteRepayParams) (contract_reference/aave/Pool/rev11.sol#2229-2316) ignores return value by ValidationLogic.validateHealthFactor(reservesData,reservesList,eModeCategories,onBehalfOfConfig,params.user,params.userEModeCategory,params.oracle) (contract_reference/aave/Pool/rev11.sol#2296-2304)
PoolLogic.executeGetUserAccountData(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.CalculateUserAccountDataParams) (contract_reference/aave/Pool/rev11.sol#2865-2887) ignores return value by (totalCollateralBase,totalDebtBase,ltv,currentLiquidationThreshold,healthFactor,None) = GenericLogic.calculateUserAccountData(reservesData,reservesList,eModeCategories,params) (contract_reference/aave/Pool/rev11.sol#2882-2884)
IsolationModeLogic.reduceIsolatedDebtIfIsolated(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),DataTypes.UserConfigurationMap,DataTypes.ReserveCache,uint256) (contract_reference/aave/Pool/rev11.sol#3117-3130) ignores return value by (isolationModeActive,isolationModeCollateralAddress,None) = userConfig.getIsolationModeState(reservesData,reservesList) (contract_reference/aave/Pool/rev11.sol#3124-3125)
ValidationLogic.validateSupply(DataTypes.ReserveCache,DataTypes.ReserveData,uint256,address) (contract_reference/aave/Pool/rev11.sol#3928-3951) ignores return value by (isActive,isFrozen,None,isPaused) = reserveCache.reserveConfiguration.getFlags() (contract_reference/aave/Pool/rev11.sol#3936)
ValidationLogic.validateWithdraw(DataTypes.ReserveCache,uint256,uint256) (contract_reference/aave/Pool/rev11.sol#3959-3970) ignores return value by (isActive,None,None,isPaused) = reserveCache.reserveConfiguration.getFlags() (contract_reference/aave/Pool/rev11.sol#3967)
ValidationLogic.validateRepay(address,DataTypes.ReserveCache,uint256,DataTypes.InterestRateMode,address,uint256) (contract_reference/aave/Pool/rev11.sol#4073-4090) ignores return value by (isActive,None,None,isPaused) = reserveCache.reserveConfiguration.getFlags() (contract_reference/aave/Pool/rev11.sol#4085)
ValidationLogic.validateSetUseReserveAsCollateral(DataTypes.ReserveConfigurationMap) (contract_reference/aave/Pool/rev11.sol#4096-4100) ignores return value by (isActive,None,None,isPaused) = reserveConfig.getFlags() (contract_reference/aave/Pool/rev11.sol#4097)
ValidationLogic.validateLiquidationCall(DataTypes.UserConfigurationMap,DataTypes.ReserveData,DataTypes.ReserveData,DataTypes.ValidateLiquidationCallParams) (contract_reference/aave/Pool/rev11.sol#4155-4191) ignores return value by (vars.collateralReserveActive,None,None,vars.collateralReservePaused) = collateralReserve.configuration.getFlags() (contract_reference/aave/Pool/rev11.sol#4165)
ValidationLogic.validateLiquidationCall(DataTypes.UserConfigurationMap,DataTypes.ReserveData,DataTypes.ReserveData,DataTypes.ValidateLiquidationCallParams) (contract_reference/aave/Pool/rev11.sol#4155-4191) ignores return value by (vars.principalReserveActive,None,None,vars.principalReservePaused) = params.debtReserveCache.reserveConfiguration.getFlags() (contract_reference/aave/Pool/rev11.sol#4167-4168)
ValidationLogic.validateHealthFactor(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.UserConfigurationMap,address,uint8,address) (contract_reference/aave/Pool/rev11.sol#4203-4224) ignores return value by (None,None,None,None,healthFactor,hasZeroLtvCollateral) = GenericLogic.calculateUserAccountData(reservesData,reservesList,eModeCategories,DataTypes.CalculateUserAccountDataParams({userConfig:userConfig,user:user,oracle:oracle,userEModeCategory:userEModeCategory})) (contract_reference/aave/Pool/rev11.sol#4212-4219)
ValidationLogic.validateHFAndLtv(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.UserConfigurationMap,address,uint8,address) (contract_reference/aave/Pool/rev11.sol#4238-4269) ignores return value by (userCollateralInBaseCurrency,userDebtInBaseCurrency,currentLtv,None,healthFactor,None) = GenericLogic.calculateUserAccountData(reservesData,reservesList,eModeCategories,DataTypes.CalculateUserAccountDataParams({userConfig:userConfig,user:user,oracle:oracle,userEModeCategory:userEModeCategory})) (contract_reference/aave/Pool/rev11.sol#4247-4259)
ValidationLogic.validateUseAsCollateral(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.UserConfigurationMap,DataTypes.ReserveConfigurationMap,address,uint8) (contract_reference/aave/Pool/rev11.sol#4403-4422) ignores return value by (isolationModeActive,None,None) = userConfig.getIsolationModeState(reservesData,reservesList) (contract_reference/aave/Pool/rev11.sol#4419)
SupplyLogic.executeSetUserEMode(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),mapping(address => uint8),DataTypes.UserConfigurationMap,address,address,uint8) (contract_reference/aave/Pool/rev11.sol#4973-4993) ignores return value by ValidationLogic.validateHealthFactor(reservesData,reservesList,eModeCategories,userConfig,user,categoryId,oracle) (contract_reference/aave/Pool/rev11.sol#4989-4991)
LiquidationLogic.executeEliminateDeficit(mapping(address => DataTypes.ReserveData),DataTypes.UserConfigurationMap,DataTypes.ExecuteEliminateDeficitParams) (contract_reference/aave/Pool/rev11.sol#5085-5136) ignores return value by IAToken(reserveCache.aTokenAddress).burn({from:params.user,receiverOfUnderlying:reserveCache.aTokenAddress,amount:balanceWriteOff,scaledAmount:scaledBalanceWriteOff,index:reserveCache.nextLiquidityIndex}) (contract_reference/aave/Pool/rev11.sol#5118-5125)
LiquidationLogic.executeLiquidationCall(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(address => DataTypes.UserConfigurationMap),mapping(uint8 => DataTypes.EModeCategory),DataTypes.ExecuteLiquidationCallParams) (contract_reference/aave/Pool/rev11.sol#5170-5397) ignores return value by (vars.totalCollateralInBaseCurrency,vars.totalDebtInBaseCurrency,None,None,vars.healthFactor,None) = GenericLogic.calculateUserAccountData(reservesData,reservesList,eModeCategories,DataTypes.CalculateUserAccountDataParams({userConfig:borrowerConfig,user:params.borrower,oracle:params.priceOracle,userEModeCategory:params.borrowerEModeCategory})) (contract_reference/aave/Pool/rev11.sol#5187-5198)
LiquidationLogic._burnCollateralATokens(DataTypes.ReserveData,DataTypes.ExecuteLiquidationCallParams,LiquidationLogic.LiquidationCallLocalVars) (contract_reference/aave/Pool/rev11.sol#5406-5429) ignores return value by IAToken(vars.collateralReserveCache.aTokenAddress).burn({from:params.borrower,receiverOfUnderlying:params.liquidator,amount:vars.actualCollateralToLiquidate,scaledAmount:vars.actualCollateralToLiquidate.getATokenBurnScaledAmount(vars.collateralReserveCache.nextLiquidityIndex),index:vars.collateralReserveCache.nextLiquidityIndex}) (contract_reference/aave/Pool/rev11.sol#5420-5428)
LiquidationLogic._burnBadDebt(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),DataTypes.UserConfigurationMap,DataTypes.ExecuteLiquidationCallParams) (contract_reference/aave/Pool/rev11.sol#5573-5611) ignores return value by (unsafe_cachedBorrowerConfig,isBorrowed,None) = UserConfiguration.getNextFlags(unsafe_cachedBorrowerConfig) (contract_reference/aave/Pool/rev11.sol#5584)
Pool.getUserAccountData(address) (contract_reference/aave/Pool/rev11.sol#8625-8650) ignores return value by PoolLogic.executeGetUserAccountData(_reserves,_reservesList,_eModeCategories,DataTypes.CalculateUserAccountDataParams({userConfig:_usersConfig[user],user:user,oracle:ADDRESSES_PROVIDER.getPriceOracle(),userEModeCategory:_usersEModeCategory[user]})) (contract_reference/aave/Pool/rev11.sol#8639-8649)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#unused-return

Detector: calls-loop
PoolLogic.executeMintToTreasury(mapping(address => DataTypes.ReserveData),address[]) (contract_reference/aave/Pool/rev11.sol#2777-2804) has external calls inside a loop: IAToken(reserve.aTokenAddress).mintToTreasury(accruedToTreasury,normalizedIncome) (contract_reference/aave/Pool/rev11.sol#2795)
LiquidationLogic._burnBadDebt(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),DataTypes.UserConfigurationMap,DataTypes.ExecuteLiquidationCallParams) (contract_reference/aave/Pool/rev11.sol#5573-5611) has external calls inside a loop: _burnDebtTokens(reserveCache,reservesData[reserveAddress],borrowerConfig,params.borrower,reserveAddress,IVariableDebtToken(reserveCache.variableDebtTokenAddress).scaledBalanceOf(params.borrower).getVTokenBalance(reserveCache.nextVariableBorrowIndex),0,true,params.interestRateStrategyAddress) (contract_reference/aave/Pool/rev11.sol#5592-5603)
	Calls stack containing the loop:
		LiquidationLogic.executeLiquidationCall(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(address => DataTypes.UserConfigurationMap),mapping(uint8 => DataTypes.EModeCategory),DataTypes.ExecuteLiquidationCallParams)
FlashLoanLogic.executeFlashLoan(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.UserConfigurationMap,DataTypes.FlashloanParams) (contract_reference/aave/Pool/rev11.sol#8066-8163) has external calls inside a loop: IAToken(reservesData[params.assets[i]].aTokenAddress).transferUnderlyingTo(params.receiverAddress,vars.currentAmount) (contract_reference/aave/Pool/rev11.sol#8096-8097)
FlashLoanLogic.executeFlashLoan(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.UserConfigurationMap,DataTypes.FlashloanParams) (contract_reference/aave/Pool/rev11.sol#8066-8163) has external calls inside a loop: BorrowLogic.executeBorrow(reservesData,reservesList,eModeCategories,userConfig,DataTypes.ExecuteBorrowParams({asset:vars.currentAsset,interestRateStrategyAddress:params.interestRateStrategyAddress,user:params.user,onBehalfOf:params.onBehalfOf,amount:vars.currentAmount,interestRateMode:DataTypes.InterestRateMode(params.interestRateModes[i_scope_0]),referralCode:params.referralCode,releaseUnderlying:false,oracle:IPoolAddressesProvider(params.addressesProvider).getPriceOracle(),userEModeCategory:IPool(params.pool).getUserEMode(params.onBehalfOf).toUint8(),priceOracleSentinel:IPoolAddressesProvider(params.addressesProvider).getPriceOracleSentinel()})) (contract_reference/aave/Pool/rev11.sol#8129-8147)
Multicall.multicall(bytes[]) (contract_reference/aave/Pool/rev11.sol#5013-5029) has external calls inside a loop: (success,result) = address(this).delegatecall(data[i]) (contract_reference/aave/Pool/rev11.sol#5017)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation/#calls-inside-a-loop

Detector: reentrancy-events
Reentrancy in LiquidationLogic._burnDebtTokens(DataTypes.ReserveCache,DataTypes.ReserveData,DataTypes.UserConfigurationMap,address,address,uint256,uint256,bool,address) (contract_reference/aave/Pool/rev11.sol#5443-5485):
	External calls:
	- (noMoreDebt,debtReserveCache.nextScaledVariableDebt) = IVariableDebtToken(debtReserveCache.variableDebtTokenAddress).burn({from:borrower,scaledAmount:burnAmount.getVTokenBurnScaledAmount(debtReserveCache.nextVariableBorrowIndex),index:debtReserveCache.nextVariableBorrowIndex}) (contract_reference/aave/Pool/rev11.sol#5462-5469)
	Event emitted after the call(s):
	- IPool.DeficitCreated(borrower,debtAsset,outstandingDebt) (contract_reference/aave/Pool/rev11.sol#5475)
Reentrancy in BorrowLogic.executeBorrow(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.UserConfigurationMap,DataTypes.ExecuteBorrowParams) (contract_reference/aave/Pool/rev11.sol#2142-2216):
	External calls:
	- reserveCache.nextScaledVariableDebt = IVariableDebtToken(reserveCache.variableDebtTokenAddress).mint(params.user,params.onBehalfOf,params.amount,amountScaled,reserveCache.nextVariableBorrowIndex) (contract_reference/aave/Pool/rev11.sol#2173-2174)
	- IAToken(reserveCache.aTokenAddress).transferUnderlyingTo(params.user,params.amount) (contract_reference/aave/Pool/rev11.sol#2194)
	Event emitted after the call(s):
	- IPool.Borrow(params.asset,params.user,params.onBehalfOf,params.amount,DataTypes.InterestRateMode.VARIABLE,reserve.currentVariableBorrowRate,params.referralCode) (contract_reference/aave/Pool/rev11.sol#2207-2215)
Reentrancy in LiquidationLogic.executeEliminateDeficit(mapping(address => DataTypes.ReserveData),DataTypes.UserConfigurationMap,DataTypes.ExecuteEliminateDeficitParams) (contract_reference/aave/Pool/rev11.sol#5085-5136):
	External calls:
	- IAToken(reserveCache.aTokenAddress).burn({from:params.user,receiverOfUnderlying:reserveCache.aTokenAddress,amount:balanceWriteOff,scaledAmount:scaledBalanceWriteOff,index:reserveCache.nextLiquidityIndex}) (contract_reference/aave/Pool/rev11.sol#5118-5125)
	Event emitted after the call(s):
	- IPool.DeficitCovered(params.asset,params.user,balanceWriteOff) (contract_reference/aave/Pool/rev11.sol#5133)
Reentrancy in FlashLoanLogic.executeFlashLoan(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.UserConfigurationMap,DataTypes.FlashloanParams) (contract_reference/aave/Pool/rev11.sol#8066-8163):
	External calls:
	- IAToken(reservesData[params.assets[i]].aTokenAddress).transferUnderlyingTo(params.receiverAddress,vars.currentAmount) (contract_reference/aave/Pool/rev11.sol#8096-8097)
	- require(bool,error)(vars.receiver.executeOperation(params.assets,params.amounts,vars.totalPremiums,params.user,params.params),Errors.InvalidFlashloanExecutorReturn()) (contract_reference/aave/Pool/rev11.sol#8103-8107)
	- BorrowLogic.executeBorrow(reservesData,reservesList,eModeCategories,userConfig,DataTypes.ExecuteBorrowParams({asset:vars.currentAsset,interestRateStrategyAddress:params.interestRateStrategyAddress,user:params.user,onBehalfOf:params.onBehalfOf,amount:vars.currentAmount,interestRateMode:DataTypes.InterestRateMode(params.interestRateModes[i_scope_0]),referralCode:params.referralCode,releaseUnderlying:false,oracle:IPoolAddressesProvider(params.addressesProvider).getPriceOracle(),userEModeCategory:IPool(params.pool).getUserEMode(params.onBehalfOf).toUint8(),priceOracleSentinel:IPoolAddressesProvider(params.addressesProvider).getPriceOracleSentinel()})) (contract_reference/aave/Pool/rev11.sol#8129-8147)
	Event emitted after the call(s):
	- IPool.FlashLoan(params.receiverAddress,params.user,params.asset,params.amount,DataTypes.InterestRateMode.NONE,params.totalPremium,params.referralCode) (contract_reference/aave/Pool/rev11.sol#8237-8245)
		- _handleFlashLoanRepayment(reservesData[vars.currentAsset],DataTypes.FlashLoanRepaymentParams({user:params.user,asset:vars.currentAsset,interestRateStrategyAddress:params.interestRateStrategyAddress,receiverAddress:params.receiverAddress,amount:vars.currentAmount,totalPremium:vars.totalPremiums[i_scope_0],referralCode:params.referralCode})) (contract_reference/aave/Pool/rev11.sol#8114-8125)
	- IPool.FlashLoan(params.receiverAddress,params.user,vars.currentAsset,vars.currentAmount,DataTypes.InterestRateMode(params.interestRateModes[i_scope_0]),0,params.referralCode) (contract_reference/aave/Pool/rev11.sol#8149-8157)
	- IPool.ReserveDataUpdated(reserveAddress,nextLiquidityRate,0,nextVariableRate,reserveCache.nextLiquidityIndex,reserveCache.nextVariableBorrowIndex) (contract_reference/aave/Pool/rev11.sol#6977-6984)
		- _handleFlashLoanRepayment(reservesData[vars.currentAsset],DataTypes.FlashLoanRepaymentParams({user:params.user,asset:vars.currentAsset,interestRateStrategyAddress:params.interestRateStrategyAddress,receiverAddress:params.receiverAddress,amount:vars.currentAmount,totalPremium:vars.totalPremiums[i_scope_0],referralCode:params.referralCode})) (contract_reference/aave/Pool/rev11.sol#8114-8125)
Reentrancy in FlashLoanLogic.executeFlashLoanSimple(DataTypes.ReserveData,DataTypes.FlashloanSimpleParams) (contract_reference/aave/Pool/rev11.sol#8175-8209):
	External calls:
	- IAToken(reserve.aTokenAddress).transferUnderlyingTo(params.receiverAddress,params.amount) (contract_reference/aave/Pool/rev11.sol#8190)
	- require(bool,error)(receiver.executeOperation(params.asset,params.amount,totalPremium,params.user,params.params),Errors.InvalidFlashloanExecutorReturn()) (contract_reference/aave/Pool/rev11.sol#8192-8195)
	Event emitted after the call(s):
	- IPool.FlashLoan(params.receiverAddress,params.user,params.asset,params.amount,DataTypes.InterestRateMode.NONE,params.totalPremium,params.referralCode) (contract_reference/aave/Pool/rev11.sol#8237-8245)
		- _handleFlashLoanRepayment(reserve,DataTypes.FlashLoanRepaymentParams({user:params.user,asset:params.asset,interestRateStrategyAddress:params.interestRateStrategyAddress,receiverAddress:params.receiverAddress,amount:params.amount,totalPremium:totalPremium,referralCode:params.referralCode})) (contract_reference/aave/Pool/rev11.sol#8197-8208)
	- IPool.ReserveDataUpdated(reserveAddress,nextLiquidityRate,0,nextVariableRate,reserveCache.nextLiquidityIndex,reserveCache.nextVariableBorrowIndex) (contract_reference/aave/Pool/rev11.sol#6977-6984)
		- _handleFlashLoanRepayment(reserve,DataTypes.FlashLoanRepaymentParams({user:params.user,asset:params.asset,interestRateStrategyAddress:params.interestRateStrategyAddress,receiverAddress:params.receiverAddress,amount:params.amount,totalPremium:totalPremium,referralCode:params.referralCode})) (contract_reference/aave/Pool/rev11.sol#8197-8208)
Reentrancy in LiquidationLogic.executeLiquidationCall(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(address => DataTypes.UserConfigurationMap),mapping(uint8 => DataTypes.EModeCategory),DataTypes.ExecuteLiquidationCallParams) (contract_reference/aave/Pool/rev11.sol#5170-5397):
	External calls:
	- _burnDebtTokens(vars.debtReserveCache,debtReserve,borrowerConfig,params.borrower,params.debtAsset,vars.borrowerReserveDebt,vars.actualDebtToLiquidate,hasNoCollateralLeft,params.interestRateStrategyAddress) (contract_reference/aave/Pool/rev11.sol#5307-5317)
		- (noMoreDebt,debtReserveCache.nextScaledVariableDebt) = IVariableDebtToken(debtReserveCache.variableDebtTokenAddress).burn({from:borrower,scaledAmount:burnAmount.getVTokenBurnScaledAmount(debtReserveCache.nextVariableBorrowIndex),index:debtReserveCache.nextVariableBorrowIndex}) (contract_reference/aave/Pool/rev11.sol#5462-5469)
	- _burnCollateralATokens(collateralReserve,params,vars) (contract_reference/aave/Pool/rev11.sol#5349)
		- IAToken(vars.collateralReserveCache.aTokenAddress).burn({from:params.borrower,receiverOfUnderlying:params.liquidator,amount:vars.actualCollateralToLiquidate,scaledAmount:vars.actualCollateralToLiquidate.getATokenBurnScaledAmount(vars.collateralReserveCache.nextLiquidityIndex),index:vars.collateralReserveCache.nextLiquidityIndex}) (contract_reference/aave/Pool/rev11.sol#5420-5428)
	Event emitted after the call(s):
	- IPool.ReserveDataUpdated(reserveAddress,nextLiquidityRate,0,nextVariableRate,reserveCache.nextLiquidityIndex,reserveCache.nextVariableBorrowIndex) (contract_reference/aave/Pool/rev11.sol#6977-6984)
		- _burnCollateralATokens(collateralReserve,params,vars) (contract_reference/aave/Pool/rev11.sol#5349)
Reentrancy in LiquidationLogic.executeLiquidationCall(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(address => DataTypes.UserConfigurationMap),mapping(uint8 => DataTypes.EModeCategory),DataTypes.ExecuteLiquidationCallParams) (contract_reference/aave/Pool/rev11.sol#5170-5397):
	External calls:
	- _burnDebtTokens(vars.debtReserveCache,debtReserve,borrowerConfig,params.borrower,params.debtAsset,vars.borrowerReserveDebt,vars.actualDebtToLiquidate,hasNoCollateralLeft,params.interestRateStrategyAddress) (contract_reference/aave/Pool/rev11.sol#5307-5317)
		- (noMoreDebt,debtReserveCache.nextScaledVariableDebt) = IVariableDebtToken(debtReserveCache.variableDebtTokenAddress).burn({from:borrower,scaledAmount:burnAmount.getVTokenBurnScaledAmount(debtReserveCache.nextVariableBorrowIndex),index:debtReserveCache.nextVariableBorrowIndex}) (contract_reference/aave/Pool/rev11.sol#5462-5469)
	- IAToken(vars.collateralReserveCache.aTokenAddress).transferOnLiquidation(params.borrower,params.liquidator,vars.actualCollateralToLiquidate,vars.actualCollateralToLiquidate.getATokenTransferScaledAmount(vars.collateralReserveCache.nextLiquidityIndex),vars.collateralReserveCache.nextLiquidityIndex) (contract_reference/aave/Pool/rev11.sol#5332-5340)
	- _burnCollateralATokens(collateralReserve,params,vars) (contract_reference/aave/Pool/rev11.sol#5349)
		- IAToken(vars.collateralReserveCache.aTokenAddress).burn({from:params.borrower,receiverOfUnderlying:params.liquidator,amount:vars.actualCollateralToLiquidate,scaledAmount:vars.actualCollateralToLiquidate.getATokenBurnScaledAmount(vars.collateralReserveCache.nextLiquidityIndex),index:vars.collateralReserveCache.nextLiquidityIndex}) (contract_reference/aave/Pool/rev11.sol#5420-5428)
	- IAToken(vars.collateralReserveCache.aTokenAddress).transferOnLiquidation({from:params.borrower,to:IAToken(vars.collateralReserveCache.aTokenAddress).RESERVE_TREASURY_ADDRESS(),amount:vars.liquidationProtocolFeeAmount,scaledAmount:scaledDownLiquidationProtocolFee,index:vars.collateralReserveCache.nextLiquidityIndex}) (contract_reference/aave/Pool/rev11.sol#5365-5372)
	- _burnBadDebt(reservesData,reservesList,borrowerConfig,params) (contract_reference/aave/Pool/rev11.sol#5379)
		- (noMoreDebt,debtReserveCache.nextScaledVariableDebt) = IVariableDebtToken(debtReserveCache.variableDebtTokenAddress).burn({from:borrower,scaledAmount:burnAmount.getVTokenBurnScaledAmount(debtReserveCache.nextVariableBorrowIndex),index:debtReserveCache.nextVariableBorrowIndex}) (contract_reference/aave/Pool/rev11.sol#5462-5469)
	Event emitted after the call(s):
	- IPool.DeficitCreated(borrower,debtAsset,outstandingDebt) (contract_reference/aave/Pool/rev11.sol#5475)
		- _burnBadDebt(reservesData,reservesList,borrowerConfig,params) (contract_reference/aave/Pool/rev11.sol#5379)
	- IPool.LiquidationCall(params.collateralAsset,params.debtAsset,params.borrower,vars.actualDebtToLiquidate,vars.actualCollateralToLiquidate,params.liquidator,params.receiveAToken) (contract_reference/aave/Pool/rev11.sol#5388-5396)
	- IPool.ReserveDataUpdated(reserveAddress,nextLiquidityRate,0,nextVariableRate,reserveCache.nextLiquidityIndex,reserveCache.nextVariableBorrowIndex) (contract_reference/aave/Pool/rev11.sol#6977-6984)
		- _burnBadDebt(reservesData,reservesList,borrowerConfig,params) (contract_reference/aave/Pool/rev11.sol#5379)
Reentrancy in PoolLogic.executeMintToTreasury(mapping(address => DataTypes.ReserveData),address[]) (contract_reference/aave/Pool/rev11.sol#2777-2804):
	External calls:
	- IAToken(reserve.aTokenAddress).mintToTreasury(accruedToTreasury,normalizedIncome) (contract_reference/aave/Pool/rev11.sol#2795)
	Event emitted after the call(s):
	- IPool.MintedToTreasury(assetAddress,amountToMint) (contract_reference/aave/Pool/rev11.sol#2797)
Reentrancy in BorrowLogic.executeRepay(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.UserConfigurationMap,DataTypes.ExecuteRepayParams) (contract_reference/aave/Pool/rev11.sol#2229-2316):
	External calls:
	- (noMoreDebt,reserveCache.nextScaledVariableDebt) = IVariableDebtToken(reserveCache.variableDebtTokenAddress).burn({from:params.onBehalfOf,scaledAmount:paybackAmount.getVTokenBurnScaledAmount(reserveCache.nextVariableBorrowIndex),index:reserveCache.nextVariableBorrowIndex}) (contract_reference/aave/Pool/rev11.sol#2260-2265)
	- zeroBalanceAfterBurn = IAToken(reserveCache.aTokenAddress).burn({from:params.user,receiverOfUnderlying:reserveCache.aTokenAddress,amount:paybackAmount,scaledAmount:paybackAmount.getATokenBurnScaledAmount(reserveCache.nextLiquidityIndex),index:reserveCache.nextLiquidityIndex}) (contract_reference/aave/Pool/rev11.sol#2282-2289)
	Event emitted after the call(s):
	- IPool.Repay(params.asset,params.onBehalfOf,params.user,paybackAmount,params.useATokens) (contract_reference/aave/Pool/rev11.sol#2313)
Reentrancy in SupplyLogic.executeSupply(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.UserConfigurationMap,DataTypes.ExecuteSupplyParams) (contract_reference/aave/Pool/rev11.sol#4731-4773):
	External calls:
	- isFirstSupply = IAToken(reserveCache.aTokenAddress).mint(params.user,params.onBehalfOf,scaledAmount,reserveCache.nextLiquidityIndex) (contract_reference/aave/Pool/rev11.sol#4755-4756)
	Event emitted after the call(s):
	- IPool.Supply(params.asset,params.user,params.onBehalfOf,params.amount,params.referralCode) (contract_reference/aave/Pool/rev11.sol#4772)
Reentrancy in SupplyLogic.executeWithdraw(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.UserConfigurationMap,DataTypes.ExecuteWithdrawParams) (contract_reference/aave/Pool/rev11.sol#4787-4852):
	External calls:
	- zeroBalanceAfterBurn = IAToken(reserveCache.aTokenAddress).burn({from:params.user,receiverOfUnderlying:params.to,amount:amountToWithdraw,scaledAmount:scaledAmountToWithdraw,index:reserveCache.nextLiquidityIndex}) (contract_reference/aave/Pool/rev11.sol#4822-4829)
	Event emitted after the call(s):
	- IPool.Withdraw(params.asset,params.user,params.to,amountToWithdraw) (contract_reference/aave/Pool/rev11.sol#4849)
Reentrancy in Pool.repayWithPermit(address,uint256,uint256,address,uint256,uint8,bytes32,bytes32) (contract_reference/aave/Pool/rev11.sol#8449-8462):
	External calls:
	- IERC20WithPermit(asset).permit(_msgSender(),address(this),amount,deadline,permitV,permitR,permitS) (contract_reference/aave/Pool/rev11.sol#8459-8460)
	- repay(asset,amount,interestRateMode,onBehalfOf) (contract_reference/aave/Pool/rev11.sol#8461)
		- BorrowLogic.executeRepay(_reserves,_reservesList,_eModeCategories,_usersConfig[onBehalfOf],DataTypes.ExecuteRepayParams({asset:asset,user:_msgSender(),interestRateStrategyAddress:RESERVE_INTEREST_RATE_STRATEGY,amount:amount,interestRateMode:DataTypes.InterestRateMode(interestRateMode),onBehalfOf:onBehalfOf,useATokens:false,oracle:ADDRESSES_PROVIDER.getPriceOracle(),userEModeCategory:_usersEModeCategory[onBehalfOf]})) (contract_reference/aave/Pool/rev11.sol#8429-8445)
		- (noMoreDebt,reserveCache.nextScaledVariableDebt) = IVariableDebtToken(reserveCache.variableDebtTokenAddress).burn({from:params.onBehalfOf,scaledAmount:paybackAmount.getVTokenBurnScaledAmount(reserveCache.nextVariableBorrowIndex),index:reserveCache.nextVariableBorrowIndex}) (contract_reference/aave/Pool/rev11.sol#2260-2265)
		- zeroBalanceAfterBurn = IAToken(reserveCache.aTokenAddress).burn({from:params.user,receiverOfUnderlying:reserveCache.aTokenAddress,amount:paybackAmount,scaledAmount:paybackAmount.getATokenBurnScaledAmount(reserveCache.nextLiquidityIndex),index:reserveCache.nextLiquidityIndex}) (contract_reference/aave/Pool/rev11.sol#2282-2289)
	Event emitted after the call(s):
	- IPool.IsolationModeTotalDebtUpdated(isolationModeCollateralAddress,newIsolationModeTotalDebt) (contract_reference/aave/Pool/rev11.sol#3171)
		- repay(asset,amount,interestRateMode,onBehalfOf) (contract_reference/aave/Pool/rev11.sol#8461)
	- IPool.Repay(params.asset,params.onBehalfOf,params.user,paybackAmount,params.useATokens) (contract_reference/aave/Pool/rev11.sol#2313)
		- repay(asset,amount,interestRateMode,onBehalfOf) (contract_reference/aave/Pool/rev11.sol#8461)
	- IPool.ReserveDataUpdated(reserveAddress,nextLiquidityRate,0,nextVariableRate,reserveCache.nextLiquidityIndex,reserveCache.nextVariableBorrowIndex) (contract_reference/aave/Pool/rev11.sol#6977-6984)
		- repay(asset,amount,interestRateMode,onBehalfOf) (contract_reference/aave/Pool/rev11.sol#8461)
	- IPool.ReserveUsedAsCollateralDisabled(asset,user) (contract_reference/aave/Pool/rev11.sol#1875)
		- repay(asset,amount,interestRateMode,onBehalfOf) (contract_reference/aave/Pool/rev11.sol#8461)
	- IPool.ReserveUsedAsCollateralEnabled(asset,user) (contract_reference/aave/Pool/rev11.sol#1872)
		- repay(asset,amount,interestRateMode,onBehalfOf) (contract_reference/aave/Pool/rev11.sol#8461)
Reentrancy in Pool.supplyWithPermit(address,uint256,address,uint16,uint256,uint8,bytes32,bytes32) (contract_reference/aave/Pool/rev11.sol#8361-8374):
	External calls:
	- IERC20WithPermit(asset).permit(_msgSender(),address(this),amount,deadline,permitV,permitR,permitS) (contract_reference/aave/Pool/rev11.sol#8371-8372)
	- supply(asset,amount,onBehalfOf,referralCode) (contract_reference/aave/Pool/rev11.sol#8373)
		- SupplyLogic.executeSupply(_reserves,_reservesList,_eModeCategories,_usersConfig[onBehalfOf],DataTypes.ExecuteSupplyParams({user:_msgSender(),asset:asset,interestRateStrategyAddress:RESERVE_INTEREST_RATE_STRATEGY,amount:amount,onBehalfOf:onBehalfOf,referralCode:referralCode,supplierEModeCategory:_usersEModeCategory[onBehalfOf]})) (contract_reference/aave/Pool/rev11.sol#8343-8357)
		- isFirstSupply = IAToken(reserveCache.aTokenAddress).mint(params.user,params.onBehalfOf,scaledAmount,reserveCache.nextLiquidityIndex) (contract_reference/aave/Pool/rev11.sol#4755-4756)
	Event emitted after the call(s):
	- IPool.ReserveDataUpdated(reserveAddress,nextLiquidityRate,0,nextVariableRate,reserveCache.nextLiquidityIndex,reserveCache.nextVariableBorrowIndex) (contract_reference/aave/Pool/rev11.sol#6977-6984)
		- supply(asset,amount,onBehalfOf,referralCode) (contract_reference/aave/Pool/rev11.sol#8373)
	- IPool.ReserveUsedAsCollateralDisabled(asset,user) (contract_reference/aave/Pool/rev11.sol#1875)
		- supply(asset,amount,onBehalfOf,referralCode) (contract_reference/aave/Pool/rev11.sol#8373)
	- IPool.ReserveUsedAsCollateralEnabled(asset,user) (contract_reference/aave/Pool/rev11.sol#1872)
		- supply(asset,amount,onBehalfOf,referralCode) (contract_reference/aave/Pool/rev11.sol#8373)
	- IPool.Supply(params.asset,params.user,params.onBehalfOf,params.amount,params.referralCode) (contract_reference/aave/Pool/rev11.sol#4772)
		- supply(asset,amount,onBehalfOf,referralCode) (contract_reference/aave/Pool/rev11.sol#8373)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#reentrancy-vulnerabilities-4

Detector: timestamp
MathUtils.calculateCompoundedInterest(uint256,uint40,uint256) (contract_reference/aave/Pool/rev11.sol#3396-3431) uses timestamp for comparisons
	Dangerous comparisons:
	- exp == 0 (contract_reference/aave/Pool/rev11.sol#3404)
ValidationLogic.validateLiquidationCall(DataTypes.UserConfigurationMap,DataTypes.ReserveData,DataTypes.ReserveData,DataTypes.ValidateLiquidationCallParams) (contract_reference/aave/Pool/rev11.sol#4155-4191) uses timestamp for comparisons
	Dangerous comparisons:
	- require(bool,error)(collateralReserve.liquidationGracePeriodUntil < uint40(block.timestamp) && debtReserve.liquidationGracePeriodUntil < uint40(block.timestamp),Errors.LiquidationGraceSentinelCheckFailed()) (contract_reference/aave/Pool/rev11.sol#4180-4184)
ReserveLogic.getNormalizedIncome(DataTypes.ReserveData) (contract_reference/aave/Pool/rev11.sol#6861-6873) uses timestamp for comparisons
	Dangerous comparisons:
	- timestamp == block.timestamp (contract_reference/aave/Pool/rev11.sol#6865)
ReserveLogic.getNormalizedDebt(DataTypes.ReserveData) (contract_reference/aave/Pool/rev11.sol#6882-6893) uses timestamp for comparisons
	Dangerous comparisons:
	- timestamp == block.timestamp (contract_reference/aave/Pool/rev11.sol#6886)
ReserveLogic.updateState(DataTypes.ReserveData,DataTypes.ReserveCache) (contract_reference/aave/Pool/rev11.sol#6900-6913) uses timestamp for comparisons
	Dangerous comparisons:
	- reserveCache.reserveLastUpdateTimestamp == uint40(block.timestamp) (contract_reference/aave/Pool/rev11.sol#6903)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#block-timestamp

Detector: assembly
GPv2SafeERC20.safeTransfer(IERC20,address,uint256) (contract_reference/aave/Pool/rev11.sol#1718-1735) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#1722-1732)
GPv2SafeERC20.safeTransferFrom(IERC20,address,address,uint256) (contract_reference/aave/Pool/rev11.sol#1739-1757) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#1743-1754)
GPv2SafeERC20.getLastTransferResult(IERC20) (contract_reference/aave/Pool/rev11.sol#1762-1820) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#1770-1819)
GPv2SafeERC20.getLastTransferResult.asm_0.revertWithMessage() (contract_reference/aave/Pool/rev11.sol#1783-1789) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#1783-1789)
UserConfiguration._getFirstAssetIdByMask(DataTypes.UserConfigurationMap,uint256) (contract_reference/aave/Pool/rev11.sol#2050-2067) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#2062-2064)
WadRayMath.wadMul(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#3221-3230) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#3223-3229)
WadRayMath.wadDiv(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#3239-3248) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#3241-3247)
WadRayMath.rayMul(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#3250-3258) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#3251-3257)
WadRayMath.rayMulFloor(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#3260-3269) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#3261-3268)
WadRayMath.rayMulCeil(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#3271-3281) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#3272-3280)
WadRayMath.rayDiv(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#3290-3298) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#3291-3297)
WadRayMath.rayDivCeil(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#3300-3309) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#3301-3308)
WadRayMath.rayDivFloor(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#3311-3319) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#3312-3318)
WadRayMath.rayToWad(uint256) (contract_reference/aave/Pool/rev11.sol#3327-3335) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#3328-3334)
WadRayMath.wadToRay(uint256) (contract_reference/aave/Pool/rev11.sol#3343-3352) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#3345-3351)
MathUtils.mulDivCeil(uint256,uint256,uint256) (contract_reference/aave/Pool/rev11.sol#3443-3458) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#3444-3457)
VersionedInitializable.isConstructor() (contract_reference/aave/Pool/rev11.sol#3544-3556) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#3552-3554)
Multicall.multicall(bytes[]) (contract_reference/aave/Pool/rev11.sol#5013-5029) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#5019-5021)
SafeCast.toUint(bool) (contract_reference/aave/Pool/rev11.sol#6833-6837) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#6834-6836)
PercentageMath.percentMul(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#7209-7218) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#7211-7217)
PercentageMath.percentMulCeil(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#7220-7230) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#7222-7229)
PercentageMath.percentMulFloor(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#7232-7241) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#7234-7240)
PercentageMath.percentDiv(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#7250-7262) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#7252-7261)
PercentageMath.percentDivCeil(uint256,uint256) (contract_reference/aave/Pool/rev11.sol#7264-7273) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#7266-7272)
Address.isContract(address) (contract_reference/aave/Pool/rev11.sol#7301-7311) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#7307-7309)
Address.verifyCallResult(bool,bytes,string) (contract_reference/aave/Pool/rev11.sol#7462-7482) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#7474-7477)
Address._revert(bytes) (contract_reference/aave/Pool/rev11.sol#7513-7522) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#7515-7518)
Pool.getReservesList() (contract_reference/aave/Pool/rev11.sol#8685-8710) uses assembly
	- INLINE ASM (contract_reference/aave/Pool/rev11.sol#8706-8708)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#assembly-usage

Detector: boolean-equal
Pool.renouncePositionManagerRole(address) (contract_reference/aave/Pool/rev11.sol#8986-8990) compares to a boolean constant:
	-_positionManager[user][_msgSender()] == false (contract_reference/aave/Pool/rev11.sol#8987)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#boolean-equality

Detector: cyclomatic-complexity
GenericLogic.calculateUserAccountData(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(uint8 => DataTypes.EModeCategory),DataTypes.CalculateUserAccountDataParams) (contract_reference/aave/Pool/rev11.sol#2367-2469) has a high cyclomatic complexity (12).
LiquidationLogic.executeLiquidationCall(mapping(address => DataTypes.ReserveData),mapping(uint256 => address),mapping(address => DataTypes.UserConfigurationMap),mapping(uint8 => DataTypes.EModeCategory),DataTypes.ExecuteLiquidationCallParams) (contract_reference/aave/Pool/rev11.sol#5170-5397) has a high cyclomatic complexity (13).
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#cyclomatic-complexity

Detector: dead-code
Context._contextSuffixLength() (contract_reference/aave/Pool/rev11.sol#943-945) is never used and should be removed
Context._msgData() (contract_reference/aave/Pool/rev11.sol#939-941) is never used and should be removed
IncentivizedERC20._setDecimals(uint8) (contract_reference/aave/Pool/rev11.sol#8025-8027) is never used and should be removed
IncentivizedERC20._setName(string) (contract_reference/aave/Pool/rev11.sol#8009-8011) is never used and should be removed
IncentivizedERC20._setSymbol(string) (contract_reference/aave/Pool/rev11.sol#8017-8019) is never used and should be removed
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#dead-code

Detector: low-level-calls
Low level call in Multicall.multicall(bytes[]) (contract_reference/aave/Pool/rev11.sol#5013-5029):
	- (success,result) = address(this).delegatecall(data[i]) (contract_reference/aave/Pool/rev11.sol#5017)
Low level call in Address.sendValue(address,uint256) (contract_reference/aave/Pool/rev11.sol#7329-7334):
	- (success,None) = recipient.call{value: amount}() (contract_reference/aave/Pool/rev11.sol#7332)
Low level call in Address.functionCallWithValue(address,bytes,uint256,string) (contract_reference/aave/Pool/rev11.sol#7392-7401):
	- (success,returndata) = target.call{value: value}(data) (contract_reference/aave/Pool/rev11.sol#7399)
Low level call in Address.functionStaticCall(address,bytes,string) (contract_reference/aave/Pool/rev11.sol#7419-7428):
	- (success,returndata) = target.staticcall(data) (contract_reference/aave/Pool/rev11.sol#7426)
Low level call in Address.functionDelegateCall(address,bytes,string) (contract_reference/aave/Pool/rev11.sol#7446-7454):
	- (success,returndata) = target.delegatecall(data) (contract_reference/aave/Pool/rev11.sol#7452)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#low-level-calls

Detector: naming-convention
Function IFlashLoanReceiver.ADDRESSES_PROVIDER() (contract_reference/aave/Pool/rev11.sol#30) is not in mixedCase
Function IFlashLoanReceiver.POOL() (contract_reference/aave/Pool/rev11.sol#32) is not in mixedCase
Function IPriceOracleGetter.BASE_CURRENCY() (contract_reference/aave/Pool/rev11.sol#46) is not in mixedCase
Function IPriceOracleGetter.BASE_CURRENCY_UNIT() (contract_reference/aave/Pool/rev11.sol#53) is not in mixedCase
Function IPool.ADDRESSES_PROVIDER() (contract_reference/aave/Pool/rev11.sol#601) is not in mixedCase
Function IPool.RESERVE_INTEREST_RATE_STRATEGY() (contract_reference/aave/Pool/rev11.sol#607) is not in mixedCase
Function IPool.FLASHLOAN_PREMIUM_TOTAL() (contract_reference/aave/Pool/rev11.sol#735) is not in mixedCase
Function IPool.FLASHLOAN_PREMIUM_TO_PROTOCOL() (contract_reference/aave/Pool/rev11.sol#743) is not in mixedCase
Function IPool.MAX_NUMBER_RESERVES() (contract_reference/aave/Pool/rev11.sol#749) is not in mixedCase
Variable PoolStorage.__DEPRECATED_bridgeProtocolFee (contract_reference/aave/Pool/rev11.sol#902) is not in mixedCase
Variable PoolStorage.__DEPRECATED_flashLoanPremiumToProtocol (contract_reference/aave/Pool/rev11.sol#910) is not in mixedCase
Variable PoolStorage.__DEPRECATED_maxStableRateBorrowSizePercent (contract_reference/aave/Pool/rev11.sol#913) is not in mixedCase
Function IACLManager.ADDRESSES_PROVIDER() (contract_reference/aave/Pool/rev11.sol#1089) is not in mixedCase
Function IACLManager.POOL_ADMIN_ROLE() (contract_reference/aave/Pool/rev11.sol#1095) is not in mixedCase
Function IACLManager.EMERGENCY_ADMIN_ROLE() (contract_reference/aave/Pool/rev11.sol#1101) is not in mixedCase
Function IACLManager.RISK_ADMIN_ROLE() (contract_reference/aave/Pool/rev11.sol#1107) is not in mixedCase
Function IACLManager.FLASH_BORROWER_ROLE() (contract_reference/aave/Pool/rev11.sol#1113) is not in mixedCase
Function IACLManager.BRIDGE_ROLE() (contract_reference/aave/Pool/rev11.sol#1119) is not in mixedCase
Function IACLManager.ASSET_LISTING_ADMIN_ROLE() (contract_reference/aave/Pool/rev11.sol#1125) is not in mixedCase
Parameter GPv2SafeERC20.getLastTransferResult.asm_0.revertWithMessage().length_getLastTransferResult_asm_0_revertWithMessage (contract_reference/aave/Pool/rev11.sol#1783) is not in mixedCase
Parameter GPv2SafeERC20.getLastTransferResult.asm_0.revertWithMessage().message_getLastTransferResult_asm_0_revertWithMessage (contract_reference/aave/Pool/rev11.sol#1783) is not in mixedCase
Function IFlashLoanSimpleReceiver.ADDRESSES_PROVIDER() (contract_reference/aave/Pool/rev11.sol#2565) is not in mixedCase
Function IFlashLoanSimpleReceiver.POOL() (contract_reference/aave/Pool/rev11.sol#2567) is not in mixedCase
Function IPriceOracleSentinel.ADDRESSES_PROVIDER() (contract_reference/aave/Pool/rev11.sol#2652) is not in mixedCase
Variable VersionedInitializable.______gap (contract_reference/aave/Pool/rev11.sol#3559) is not in mixedCase
Function IAToken.UNDERLYING_ASSET_ADDRESS() (contract_reference/aave/Pool/rev11.sol#7641) is not in mixedCase
Function IAToken.RESERVE_TREASURY_ADDRESS() (contract_reference/aave/Pool/rev11.sol#7647) is not in mixedCase
Function IAToken.DOMAIN_SEPARATOR() (contract_reference/aave/Pool/rev11.sol#7654) is not in mixedCase
Function IVariableDebtToken.UNDERLYING_ASSET_ADDRESS() (contract_reference/aave/Pool/rev11.sol#7763) is not in mixedCase
Variable IncentivizedERC20.__deprecated_incentivesController (contract_reference/aave/Pool/rev11.sol#7816) is not in mixedCase
Variable IncentivizedERC20.POOL (contract_reference/aave/Pool/rev11.sol#7818) is not in mixedCase
Variable IncentivizedERC20.REWARDS_CONTROLLER (contract_reference/aave/Pool/rev11.sol#7823) is not in mixedCase
Function Pool.FLASHLOAN_PREMIUM_TOTAL() (contract_reference/aave/Pool/rev11.sol#8723-8725) is not in mixedCase
Function Pool.FLASHLOAN_PREMIUM_TO_PROTOCOL() (contract_reference/aave/Pool/rev11.sol#8728-8730) is not in mixedCase
Function Pool.MAX_NUMBER_RESERVES() (contract_reference/aave/Pool/rev11.sol#8733-8735) is not in mixedCase
Variable Pool.ADDRESSES_PROVIDER (contract_reference/aave/Pool/rev11.sol#8268) is not in mixedCase
Variable Pool.RESERVE_INTEREST_RATE_STRATEGY (contract_reference/aave/Pool/rev11.sol#8270) is not in mixedCase
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#conformance-to-solidity-naming-conventions

Detector: too-many-digits
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- LTV_MASK = 0x000000000000000000000000000000000000000000000000000000000000FFFF (contract_reference/aave/Pool/rev11.sol#1256)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- LIQUIDATION_THRESHOLD_MASK = 0x00000000000000000000000000000000000000000000000000000000FFFF0000 (contract_reference/aave/Pool/rev11.sol#1257-1258)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- LIQUIDATION_BONUS_MASK = 0x0000000000000000000000000000000000000000000000000000FFFF00000000 (contract_reference/aave/Pool/rev11.sol#1259-1260)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- DECIMALS_MASK = 0x00000000000000000000000000000000000000000000000000FF000000000000 (contract_reference/aave/Pool/rev11.sol#1261)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- ACTIVE_MASK = 0x0000000000000000000000000000000000000000000000000100000000000000 (contract_reference/aave/Pool/rev11.sol#1262)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- FROZEN_MASK = 0x0000000000000000000000000000000000000000000000000200000000000000 (contract_reference/aave/Pool/rev11.sol#1263)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- BORROWING_MASK = 0x0000000000000000000000000000000000000000000000000400000000000000 (contract_reference/aave/Pool/rev11.sol#1264)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- PAUSED_MASK = 0x0000000000000000000000000000000000000000000000001000000000000000 (contract_reference/aave/Pool/rev11.sol#1266)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- BORROWABLE_IN_ISOLATION_MASK = 0x0000000000000000000000000000000000000000000000002000000000000000 (contract_reference/aave/Pool/rev11.sol#1267-1268)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- SILOED_BORROWING_MASK = 0x0000000000000000000000000000000000000000000000004000000000000000 (contract_reference/aave/Pool/rev11.sol#1269-1270)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- FLASHLOAN_ENABLED_MASK = 0x0000000000000000000000000000000000000000000000008000000000000000 (contract_reference/aave/Pool/rev11.sol#1271-1272)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- RESERVE_FACTOR_MASK = 0x00000000000000000000000000000000000000000000FFFF0000000000000000 (contract_reference/aave/Pool/rev11.sol#1273)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- BORROW_CAP_MASK = 0x00000000000000000000000000000000000FFFFFFFFF00000000000000000000 (contract_reference/aave/Pool/rev11.sol#1274)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- SUPPLY_CAP_MASK = 0x00000000000000000000000000FFFFFFFFF00000000000000000000000000000 (contract_reference/aave/Pool/rev11.sol#1275)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- LIQUIDATION_PROTOCOL_FEE_MASK = 0x0000000000000000000000FFFF00000000000000000000000000000000000000 (contract_reference/aave/Pool/rev11.sol#1276-1277)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- DEBT_CEILING_MASK = 0x0FFFFFFFFFF00000000000000000000000000000000000000000000000000000 (contract_reference/aave/Pool/rev11.sol#1280)
ReserveConfiguration.slitherConstructorConstantVariables() (contract_reference/aave/Pool/rev11.sol#1255-1710) uses literals with too many digits:
	- VIRTUAL_ACC_ACTIVE_MASK = 0x1000000000000000000000000000000000000000000000000000000000000000 (contract_reference/aave/Pool/rev11.sol#1282-1283)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#too-many-digits

Detector: unindexed-event-address
Event IPriceOracleSentinel.SequencerOracleUpdated(address) (contract_reference/aave/Pool/rev11.sol#2640) has address parameters but no indexed parameters
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#unindexed-event-address-parameters

Detector: unused-state
PoolStorage.__DEPRECATED_bridgeProtocolFee (contract_reference/aave/Pool/rev11.sol#902) is never used in PoolInstance (contract_reference/aave/Pool/rev11.sol#9082-9103)
PoolStorage.__DEPRECATED_flashLoanPremiumToProtocol (contract_reference/aave/Pool/rev11.sol#910) is never used in PoolInstance (contract_reference/aave/Pool/rev11.sol#9082-9103)
PoolStorage.__DEPRECATED_maxStableRateBorrowSizePercent (contract_reference/aave/Pool/rev11.sol#913) is never used in PoolInstance (contract_reference/aave/Pool/rev11.sol#9082-9103)
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#unused-state-variable

Detector: constable-states
IncentivizedERC20.__deprecated_incentivesController (contract_reference/aave/Pool/rev11.sol#7816) should be constant 
IncentivizedERC20._totalSupply (contract_reference/aave/Pool/rev11.sol#7811) should be constant 
PoolStorage.__DEPRECATED_bridgeProtocolFee (contract_reference/aave/Pool/rev11.sol#902) should be constant 
PoolStorage.__DEPRECATED_flashLoanPremiumToProtocol (contract_reference/aave/Pool/rev11.sol#910) should be constant 
PoolStorage.__DEPRECATED_maxStableRateBorrowSizePercent (contract_reference/aave/Pool/rev11.sol#913) should be constant 
Reference: https://github.com/crytic/slither/wiki/Detector-Documentation#state-variables-that-could-be-declared-constant
/Volumes/PNYRP60PSSD/dev-projects/mev-arbitrum/vendor/degenbot/contract_reference/aave/Pool/rev11.sol analyzed (46 contracts with 101 detectors), 156 result(s) found

"""
Agent模型连接修复验证测试
验证修复后的Agent能够正确获取API密钥并创建模型
"""

import asyncio
import logging
import os

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_config_manager_api_keys():
    """测试ConfigManager能否正确获取API密钥"""
    logger.info("🔑 测试ConfigManager API密钥获取功能")
    
    try:
        from Item.Agentlib.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        
        # 测试各平台的API密钥获取
        platforms = ['openai', 'zhipu', 'aihubmix']
        
        for platform in platforms:
            api_key = config_manager.get_api_key(platform)
            api_base = config_manager.get_api_base(platform)
            
            logger.info(f"📋 {platform}:")
            logger.info(f"  - API Key: {'✅ 已配置' if api_key else '❌ 未配置'}")
            logger.info(f"  - API Base: {api_base or '默认'}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ConfigManager测试失败: {e}")
        return False


async def test_lightweight_agent_with_model():
    """测试轻量级Agent的模型按需创建功能"""
    logger.info("🤖 测试轻量级Agent模型按需创建")
    
    try:
        from Item.Agentlib import AgentFactory, AgentCreationConfig, AgentCreationMode
        from Item.Agentlib.Agent import AgentRole
        from Item.Agentlib.config_manager import ConfigManager
        
        # 创建AgentFactory（使用ConfigManager）
        factory = AgentFactory(ConfigManager())
        
        # 创建轻量级Agent配置
        config = AgentCreationConfig(
            name="TestAgent",
            role=AgentRole.CHAT,
            model_type="openai",  # 使用OpenAI作为测试
            model_name="gpt-3.5-turbo",
            system_prompt="你是一个测试助手",
            creation_mode=AgentCreationMode.BASIC
        )
        
        # 创建Agent
        agent = factory.create_agent(config)
        
        # 验证Agent属性
        assert hasattr(agent, '_model_config'), "Agent缺少_model_config属性"
        assert agent.model is None, "Agent不应该立即初始化模型"
        
        logger.info(f"✅ 轻量级Agent创建成功: {agent.name}")
        logger.info(f"📋 模型配置: {agent._model_config}")
        
        # 测试按需模型创建
        logger.info("🔧 测试按需模型创建...")
        await agent._create_model_on_demand()
        
        if agent.model:
            logger.info("✅ 模型按需创建成功")
            logger.info(f"📋 模型类型: {type(agent.model).__name__}")
        else:
            logger.warning("⚠️ 模型创建失败，可能是API密钥未配置")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 轻量级Agent测试失败: {e}")
        return False


async def test_agent_think_with_shared_context():
    """测试Agent.think()方法的共享上下文功能"""
    logger.info("💭 测试Agent.think()共享上下文功能")
    
    try:
        from Item.Agentlib import AgentFactory, AgentCreationConfig, AgentCreationMode
        from Item.Agentlib.Agent import AgentRole
        from Item.Agentlib.config_manager import ConfigManager
        from Item.ContextEngineer.context_manager import ContextManager
        
        # 创建共享上下文管理器
        shared_context = ContextManager("test_shared_context")
        
        # 创建轻量级Agent
        factory = AgentFactory(ConfigManager())
        config = AgentCreationConfig(
            name="ThinkTestAgent",
            role=AgentRole.CHAT,
            model_type="openai",
            model_name="gpt-3.5-turbo",
            system_prompt="你是一个思考测试助手",
            creation_mode=AgentCreationMode.BASIC
        )
        
        agent = factory.create_agent(config)
        
        # 准备输入数据
        input_data = {
            'user_input': '你好，请简单回应一下',
            'room_context': {
                'available_agents': ['ThinkTestAgent']
            }
        }
        
        # 调用think方法（使用共享上下文）
        logger.info("🧠 调用Agent.think()方法...")
        result = await agent.think(
            input_data,
            shared_context_manager=shared_context,
            connection_pool=None
        )
        
        # 检查结果
        if result.get('success'):
            logger.info("✅ Agent.think()调用成功")
            logger.info(f"📝 响应: {result.get('response', '')[:100]}...")
        else:
            logger.warning(f"⚠️ Agent.think()失败: {result.get('error', 'Unknown error')}")
        
        return result.get('success', False)
        
    except Exception as e:
        logger.error(f"❌ Agent.think()测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("🚀 Agent模型连接修复验证测试")
    logger.info("=" * 60)
    
    # 检查环境变量
    logger.info("🔍 检查环境变量配置:")
    env_vars = ['OPENAI_API_KEY', 'ZHIPU_API_KEY', 'AIHUBMIX_API_KEY']
    for var in env_vars:
        value = os.getenv(var)
        logger.info(f"  {var}: {'✅ 已设置' if value else '❌ 未设置'}")
    
    logger.info("-" * 60)
    
    # 运行测试
    tests = [
        ("ConfigManager API密钥获取", test_config_manager_api_keys),
        ("轻量级Agent模型创建", test_lightweight_agent_with_model),
        ("Agent.think()共享上下文", test_agent_think_with_shared_context)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"🧪 开始测试: {test_name}")
        try:
            success = await test_func()
            results[test_name] = success
            status = "✅ 通过" if success else "❌ 失败"
            logger.info(f"📊 {test_name}: {status}")
        except Exception as e:
            logger.error(f"💥 {test_name} 异常: {e}")
            results[test_name] = False
        
        logger.info("-" * 40)
    
    # 输出总结
    logger.info("=" * 60)
    logger.info("📊 测试结果总结:")
    logger.info("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"  {test_name}: {status}")
    
    logger.info(f"\n🎯 总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过！Agent模型连接修复成功！")
    else:
        logger.info("⚠️ 部分测试失败，请检查配置或代码")
    
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

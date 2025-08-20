"""
聊天室创建性能测试
测试优化后的轻量级Agent创建和共享上下文系统
"""

import asyncio
import time
import logging
from typing import Dict, Any

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_lightweight_agent_creation():
    """测试轻量级Agent创建性能"""
    logger.info("🚀 开始测试轻量级Agent创建性能")
    
    try:
        from Item.Agentlib.agent_factory import AgentFactory, AgentCreationConfig, AgentCreationMode
        from Item.Agentlib.Agent import AgentRole
        
        factory = AgentFactory()
        
        # 测试配置
        test_configs = [
            {
                'name': 'TestAgent1',
                'role': AgentRole.CHAT,
                'platform': 'openai',
                'model_name': 'gpt-3.5-turbo',
                'prompt': '你是一个友好的助手'
            },
            {
                'name': 'TestAgent2', 
                'role': AgentRole.ANALYST,
                'platform': 'zhipu',
                'model_name': 'glm-4',
                'prompt': '你是一个数据分析专家'
            },
            {
                'name': 'TestAgent3',
                'role': AgentRole.CREATIVE,
                'platform': 'aihubmix',
                'model_name': 'gpt-4',
                'prompt': '你是一个创意写作助手'
            }
        ]
        
        # 测试BASIC模式创建
        start_time = time.time()
        
        agents = []
        for config in test_configs:
            agent_config = AgentCreationConfig(
                name=config['name'],
                role=config['role'],
                model_type=config['platform'],
                model_name=config['model_name'],
                system_prompt=config['prompt'],
                creation_mode=AgentCreationMode.BASIC  # 轻量级模式
            )
            
            agent = factory.create_agent(agent_config)
            agents.append(agent)
            logger.info(f"✅ 创建轻量级Agent: {agent.name}")
        
        creation_time = time.time() - start_time
        logger.info(f"🎯 轻量级Agent创建完成: {len(agents)}个Agent，耗时 {creation_time:.3f}秒")
        
        # 验证Agent属性
        for agent in agents:
            assert hasattr(agent, '_model_config'), f"Agent {agent.name} 缺少模型配置"
            assert hasattr(agent, 'system_prompt'), f"Agent {agent.name} 缺少系统提示词"
            assert agent.model is None, f"Agent {agent.name} 不应该立即初始化模型"
            logger.info(f"✅ Agent {agent.name} 验证通过")
        
        return True, creation_time
        
    except Exception as e:
        logger.error(f"❌ 轻量级Agent创建测试失败: {e}")
        return False, 0


async def test_shared_context_manager():
    """测试共享上下文管理器"""
    logger.info("🚀 开始测试共享上下文管理器")
    
    try:
        from Item.ContextEngineer.context_manager import ContextManager
        
        # 创建共享上下文管理器
        start_time = time.time()
        shared_context = ContextManager("test_room_shared_context")
        creation_time = time.time() - start_time
        
        logger.info(f"✅ 共享上下文管理器创建完成，耗时 {creation_time:.3f}秒")
        
        # 测试上下文功能
        shared_context.set_user_input("测试用户输入")
        context = shared_context.build_structured_context("测试查询")
        
        assert context is not None, "上下文构建失败"
        logger.info(f"✅ 共享上下文功能验证通过")
        
        return True, creation_time
        
    except Exception as e:
        logger.error(f"❌ 共享上下文管理器测试失败: {e}")
        return False, 0


async def test_connection_pool():
    """测试连接池功能"""
    logger.info("🚀 开始测试连接池功能")
    
    try:
        from Item.Agentlib.connection_pool import get_connection_pool
        
        # 获取连接池
        start_time = time.time()
        pool = await get_connection_pool()
        creation_time = time.time() - start_time
        
        logger.info(f"✅ 连接池获取完成，耗时 {creation_time:.3f}秒")
        
        # 测试连接池状态
        stats = pool.get_stats()
        logger.info(f"📊 连接池状态: {stats}")
        
        assert stats['status'] == 'ready', "连接池状态不正确"
        logger.info(f"✅ 连接池功能验证通过")
        
        return True, creation_time
        
    except Exception as e:
        logger.error(f"❌ 连接池测试失败: {e}")
        return False, 0


async def test_room_creation_simulation():
    """模拟完整的房间创建过程"""
    logger.info("🚀 开始模拟完整房间创建过程")
    
    try:
        from Item.ChatRoom import ChatRoom, ChatRoomConfig, CommunicationMode
        from Item.Agentlib.agent_factory import AgentFactory, AgentCreationConfig, AgentCreationMode
        from Item.Agentlib.Agent import AgentRole
        
        # 1. 创建房间配置
        room_config = ChatRoomConfig(
            room_id="test_room_001",
            room_name="性能测试房间",
            description="测试轻量级Agent创建性能",
            max_agents=5,
            communication_mode=CommunicationMode.NETWORK,
            discussion_enabled=True
        )
        
        # 2. 创建ChatRoom（包含共享上下文）
        start_time = time.time()
        room = ChatRoom(room_config)
        await room.start()
        room_creation_time = time.time() - start_time
        
        logger.info(f"✅ ChatRoom创建完成，耗时 {room_creation_time:.3f}秒")
        
        # 3. 并行创建多个轻量级Agent
        agent_start_time = time.time()
        
        factory = AgentFactory()
        agent_configs = [
            ('助手1', AgentRole.CHAT, 'openai', 'gpt-3.5-turbo'),
            ('分析师', AgentRole.ANALYST, 'zhipu', 'glm-4'),
            ('创意师', AgentRole.CREATIVE, 'aihubmix', 'gpt-4')
        ]
        
        async def create_agent(name, role, platform, model_name):
            config = AgentCreationConfig(
                name=name,
                role=role,
                model_type=platform,
                model_name=model_name,
                system_prompt=f'你是{name}',
                creation_mode=AgentCreationMode.BASIC
            )
            return factory.create_agent(config)
        
        # 并行创建Agent
        agent_tasks = [create_agent(*config) for config in agent_configs]
        agents = await asyncio.gather(*agent_tasks)
        
        agent_creation_time = time.time() - agent_start_time
        
        # 4. 将Agent添加到房间
        add_start_time = time.time()
        for agent in agents:
            await room.add_agent(agent)
        add_time = time.time() - add_start_time
        
        total_time = time.time() - start_time
        
        logger.info(f"🎯 完整房间创建性能报告:")
        logger.info(f"  - ChatRoom创建: {room_creation_time:.3f}秒")
        logger.info(f"  - Agent并行创建: {agent_creation_time:.3f}秒")
        logger.info(f"  - Agent添加到房间: {add_time:.3f}秒")
        logger.info(f"  - 总耗时: {total_time:.3f}秒")
        logger.info(f"  - Agent数量: {len(agents)}个")
        
        # 清理
        await room.stop()
        
        return True, total_time
        
    except Exception as e:
        logger.error(f"❌ 房间创建模拟测试失败: {e}")
        return False, 0


async def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("🚀 SocioPulse-AI 聊天室创建性能优化测试")
    logger.info("=" * 60)
    
    results = {}
    
    # 测试1: 轻量级Agent创建
    success, time_taken = await test_lightweight_agent_creation()
    results['lightweight_agents'] = {'success': success, 'time': time_taken}
    
    # 测试2: 共享上下文管理器
    success, time_taken = await test_shared_context_manager()
    results['shared_context'] = {'success': success, 'time': time_taken}
    
    # 测试3: 连接池
    success, time_taken = await test_connection_pool()
    results['connection_pool'] = {'success': success, 'time': time_taken}
    
    # 测试4: 完整房间创建模拟
    success, time_taken = await test_room_creation_simulation()
    results['full_room_creation'] = {'success': success, 'time': time_taken}
    
    # 输出测试结果
    logger.info("=" * 60)
    logger.info("📊 测试结果汇总:")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result['success'] else "❌ 失败"
        time_str = f"{result['time']:.3f}秒" if result['success'] else "N/A"
        logger.info(f"  {test_name}: {status} ({time_str})")
    
    # 性能评估
    if results['full_room_creation']['success']:
        total_time = results['full_room_creation']['time']
        if total_time < 1.0:
            logger.info("🎉 优化目标达成！房间创建时间 < 1秒")
        elif total_time < 2.0:
            logger.info("✅ 性能良好！房间创建时间 < 2秒")
        else:
            logger.info("⚠️ 仍需优化，房间创建时间 > 2秒")
    
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

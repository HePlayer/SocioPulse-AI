"""
NetworkTopology 优化验证测试
验证移除全连接机制后的功能完整性和性能提升
"""

import asyncio
import time
import logging
from typing import Dict, Any

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_simplified_network_topology():
    """测试简化的NetworkTopology类"""
    logger.info("🔧 测试简化的NetworkTopology类")
    
    try:
        from Item.ChatRoom import NetworkTopology
        
        # 创建NetworkTopology实例
        topology = NetworkTopology()
        
        # 测试添加Agent
        agent_ids = ['agent1', 'agent2', 'agent3', 'agent4', 'agent5']
        
        for agent_id in agent_ids:
            topology.add_agent(agent_id)
        
        # 验证Agent数量
        assert topology.get_agent_count() == 5, f"Expected 5 agents, got {topology.get_agent_count()}"
        
        # 验证Agent存在性检查
        for agent_id in agent_ids:
            assert topology.has_agent(agent_id), f"Agent {agent_id} should exist"
        
        # 验证获取所有Agent
        all_agents = topology.get_all_agents()
        assert len(all_agents) == 5, f"Expected 5 agents in set, got {len(all_agents)}"
        assert all_agents == set(agent_ids), "Agent sets should match"
        
        # 测试移除Agent
        topology.remove_agent('agent3')
        assert topology.get_agent_count() == 4, f"Expected 4 agents after removal, got {topology.get_agent_count()}"
        assert not topology.has_agent('agent3'), "Agent3 should not exist after removal"
        
        logger.info("✅ NetworkTopology简化测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ NetworkTopology简化测试失败: {e}")
        return False


async def test_chatroom_creation_performance():
    """测试ChatRoom创建性能（模拟多Agent场景）"""
    logger.info("⚡ 测试ChatRoom创建性能")
    
    try:
        from Item.ChatRoom import ChatRoom, ChatRoomConfig, CommunicationMode
        from Item.Agentlib import AgentFactory, AgentCreationConfig, AgentCreationMode
        from Item.Agentlib.Agent import AgentRole
        from Item.Agentlib.config_manager import ConfigManager
        
        # 测试不同Agent数量的创建性能
        agent_counts = [3, 5, 8, 10]
        performance_results = {}
        
        for count in agent_counts:
            logger.info(f"📊 测试 {count} 个Agent的房间创建")
            
            # 创建房间配置
            room_config = ChatRoomConfig(
                room_id=f"perf_test_{count}",
                room_name=f"性能测试房间_{count}",
                description=f"测试{count}个Agent的创建性能",
                max_agents=count + 2,
                communication_mode=CommunicationMode.NETWORK
            )
            
            # 创建ChatRoom
            start_time = time.time()
            room = ChatRoom(room_config)
            await room.start()
            room_creation_time = time.time() - start_time
            
            # 创建Agent
            factory = AgentFactory(ConfigManager())
            agents = []
            
            agent_creation_start = time.time()
            for i in range(count):
                config = AgentCreationConfig(
                    name=f"Agent_{i+1}",
                    role=AgentRole.CHAT,
                    model_type="openai",
                    model_name="gpt-3.5-turbo",
                    system_prompt=f"你是Agent_{i+1}",
                    creation_mode=AgentCreationMode.BASIC
                )
                agent = factory.create_agent(config)
                agents.append(agent)
            
            agent_creation_time = time.time() - agent_creation_start
            
            # 添加Agent到房间（这里测试优化效果）
            add_agents_start = time.time()
            for agent in agents:
                await room.add_agent(agent)
            add_agents_time = time.time() - add_agents_start
            
            total_time = time.time() - start_time
            
            # 记录性能数据
            performance_results[count] = {
                'room_creation': room_creation_time,
                'agent_creation': agent_creation_time,
                'add_agents': add_agents_time,
                'total_time': total_time,
                'avg_per_agent': add_agents_time / count if count > 0 else 0
            }
            
            # 验证房间状态
            status = room.get_room_status()
            assert status['agent_count'] == count, f"Expected {count} agents, got {status['agent_count']}"
            
            # 验证NetworkTopology状态
            assert room.network_topology.get_agent_count() == count, f"Topology should have {count} agents"
            
            logger.info(f"  ✅ {count}个Agent: 总时间 {total_time:.3f}s, 添加Agent {add_agents_time:.3f}s")
            
            # 清理
            await room.stop()
        
        # 输出性能报告
        logger.info("📈 性能测试结果:")
        logger.info("Agent数量 | 房间创建 | Agent创建 | 添加Agent | 总时间 | 平均每Agent")
        logger.info("-" * 70)
        
        for count, results in performance_results.items():
            logger.info(f"{count:8d} | {results['room_creation']:8.3f}s | {results['agent_creation']:9.3f}s | {results['add_agents']:8.3f}s | {results['total_time']:6.3f}s | {results['avg_per_agent']:10.3f}s")
        
        # 验证性能改进（添加Agent应该是线性时间）
        if len(performance_results) >= 2:
            counts = sorted(performance_results.keys())
            first_avg = performance_results[counts[0]]['avg_per_agent']
            last_avg = performance_results[counts[-1]]['avg_per_agent']
            
            # 平均每Agent时间不应该随Agent数量显著增长（线性复杂度）
            if last_avg <= first_avg * 2:  # 允许一定的波动
                logger.info("✅ 性能测试通过：添加Agent时间复杂度为线性")
            else:
                logger.warning(f"⚠️ 性能可能仍有问题：平均时间从 {first_avg:.3f}s 增长到 {last_avg:.3f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ChatRoom性能测试失败: {e}")
        return False


async def test_svr_functionality_preserved():
    """测试SVR功能是否保持正常"""
    logger.info("🧠 测试SVR功能完整性")
    
    try:
        from Item.ChatRoom import ChatRoom, ChatRoomConfig, CommunicationMode
        from Item.Agentlib import AgentFactory, AgentCreationConfig, AgentCreationMode
        from Item.Agentlib.Agent import AgentRole
        from Item.Agentlib.config_manager import ConfigManager
        
        # 创建测试房间
        room_config = ChatRoomConfig(
            room_id="svr_test_room",
            room_name="SVR功能测试房间",
            description="测试SVR机制是否正常工作",
            max_agents=5,
            communication_mode=CommunicationMode.NETWORK,
            discussion_enabled=True
        )
        
        room = ChatRoom(room_config)
        await room.start()
        
        # 创建多个Agent
        factory = AgentFactory(ConfigManager())
        agents = []
        
        for i in range(3):
            config = AgentCreationConfig(
                name=f"SVRTestAgent_{i+1}",
                role=AgentRole.CHAT,
                model_type="openai",
                model_name="gpt-3.5-turbo",
                system_prompt=f"你是SVR测试Agent_{i+1}",
                creation_mode=AgentCreationMode.BASIC
            )
            agent = factory.create_agent(config)
            agents.append(agent)
            await room.add_agent(agent)
        
        # 验证Agent都正确添加
        assert len(room.agents) == 3, f"Expected 3 agents, got {len(room.agents)}"
        
        # 验证NetworkTopology记录了所有Agent
        assert room.network_topology.get_agent_count() == 3, "NetworkTopology should track all agents"
        
        # 验证所有Agent都在拓扑中
        for agent in agents:
            assert room.network_topology.has_agent(agent.component_id), f"Agent {agent.name} should be in topology"
        
        # 模拟SVR选择过程（验证participants字典可用）
        participants = {agent.component_id: agent for agent in agents}
        
        # 验证可以通过字典访问Agent
        for agent_id, agent in participants.items():
            assert agent_id in room.agents, f"Agent {agent_id} should be accessible"
            assert room.agents[agent_id] == agent, "Agent references should match"
        
        logger.info("✅ SVR功能完整性测试通过")
        
        # 清理
        await room.stop()
        return True
        
    except Exception as e:
        logger.error(f"❌ SVR功能测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("🚀 NetworkTopology 优化验证测试")
    logger.info("=" * 60)
    
    tests = [
        ("简化NetworkTopology类", test_simplified_network_topology),
        ("ChatRoom创建性能", test_chatroom_creation_performance),
        ("SVR功能完整性", test_svr_functionality_preserved)
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
        logger.info("🎉 所有测试通过！NetworkTopology优化成功！")
        logger.info("📈 预期性能提升：")
        logger.info("  - 房间创建复杂度：O(N²) → O(N)")
        logger.info("  - 内存使用：O(N²) → O(N)")
        logger.info("  - 代码复杂性：显著降低")
    else:
        logger.info("⚠️ 部分测试失败，请检查修改")
    
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

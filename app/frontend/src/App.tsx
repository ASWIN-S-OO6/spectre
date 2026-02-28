import React, { useState, useEffect, useRef } from 'react';
import { Typography, Input, Button, Select, Switch, Space, Form, ConfigProvider, theme, Tooltip } from 'antd';
import { SendOutlined, SafetyOutlined, RobotOutlined, CodeOutlined, GlobalOutlined, DesktopOutlined, SettingOutlined } from '@ant-design/icons';
import { io, Socket } from 'socket.io-client';

const { Title, Text } = Typography;

interface OutputLine {
  text: string;
  color?: string;
  terminalId?: string;
}

interface TerminalWindow {
  id: string;
  isMaximized: boolean;
  isMinimized: boolean;
  zIndex: number;
  command: string;
  history: string[];
  historyIndex: number;
}

interface SystemLog {
  id: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'success';
  source: string;
  message: string;
}

const App: React.FC = () => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const [username, setUsername] = useState('spectre');
  const [hostname, setHostname] = useState('kali');

  // OS Windows Manager
  const [isSettingsOpen, setIsSettingsOpen] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [terminals, setTerminals] = useState<TerminalWindow[]>([]);
  const [activeWindowId, setActiveWindowId] = useState<string | null>(null);

  // Global Terminal & System Logs
  const [outputs, setOutputs] = useState<OutputLine[]>([]);
  const [systemLogs, setSystemLogs] = useState<SystemLog[]>([]);
  const sidebarScrollRef = useRef<HTMLDivElement | null>(null);

  // App state
  const [agentMode, setAgentMode] = useState(true);
  const [torStatus, setTorStatus] = useState<{ status: string; ip?: string }>({ status: 'Off' });
  const [isInitializing, setIsInitializing] = useState(false);

  useEffect(() => {
    const newSocket = io();
    setSocket(newSocket);

    newSocket.on('output', (data: { text: string; color?: string; terminalId?: string }) => {
      setOutputs(prev => [...prev, data]);
    });

    newSocket.on('authenticated', (data: { ok: boolean }) => {
      if (data.ok) {
        setIsAuthenticated(true);
        setIsSettingsOpen(false);
        setIsInitializing(false);
      }
    });

    newSocket.on('clear', (data: { terminalId?: string }) => {
      setOutputs(prev => prev.filter(o => o.terminalId !== data.terminalId));
    });

    newSocket.on('system_log', (data: Omit<SystemLog, 'id' | 'timestamp'>) => {
      setSystemLogs(prev => [...prev, {
        ...data,
        id: `syslog_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false, hour: "numeric", minute: "numeric", second: "numeric" })
      }]);
    });

    newSocket.on('tor_ip_update', (data: { status: string; ip?: string }) => {
      setTorStatus({ status: data.status, ip: data.ip });
    });

    return () => {
      newSocket.disconnect();
    };
  }, []);

  useEffect(() => {
    terminals.forEach(term => {
      const el = document.getElementById(`term-scroll-${term.id}`);
      if (el) el.scrollTop = el.scrollHeight;
    });
  }, [outputs, terminals]);

  useEffect(() => {
    if (sidebarScrollRef.current) {
      sidebarScrollRef.current.scrollTop = sidebarScrollRef.current.scrollHeight;
    }
  }, [systemLogs]);

  const spawnTerminal = () => {
    const newId = `term_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
    setTerminals(prev => {
      const highestZ = Math.max(0, ...prev.map(t => t.zIndex));
      return [
        ...prev,
        {
          id: newId,
          isMaximized: false,
          isMinimized: false,
          zIndex: highestZ + 1,
          command: '',
          history: [],
          historyIndex: -1
        }
      ];
    });
    setActiveWindowId(newId);
  };

  const closeTerminal = (id: string) => {
    setTerminals(prev => prev.filter(t => t.id !== id));
    setOutputs(prev => prev.filter(o => o.terminalId !== id)); // Clear outputs for closed terminal
    if (activeWindowId === id) {
      setActiveWindowId(terminals.length > 1 ? terminals[0]?.id || null : null);
    }
  };

  const updateTerminal = (id: string, updates: Partial<TerminalWindow>) => {
    setTerminals(prev => prev.map(t => t.id === id ? { ...t, ...updates } : t));
  };

  const focusTerminal = (id: string) => {
    setActiveWindowId(id);
    setTerminals(prev => {
      const highestZ = Math.max(0, ...prev.map(t => t.zIndex));
      return prev.map(t => t.id === id ? { ...t, zIndex: highestZ + 1 } : t);
    });
  };

  const handleInit = (values: any) => {
    if (!socket) return;
    if (!values.apiKey && values.agentMode) {
      alert("API Key is required for Agent Mode.");
      return;
    }

    setIsInitializing(true);
    setAgentMode(values.agentMode);
    setUsername(values.username || 'spectre');
    setHostname(values.hostname || 'kali');

    const firstTermId = `term_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
    setTerminals([{
      id: firstTermId,
      isMaximized: false,
      isMinimized: false,
      zIndex: 1,
      command: '',
      history: [],
      historyIndex: -1
    }]);
    setActiveWindowId(firstTermId);

    socket.emit('set_api_key', {
      key: values.apiKey || '',
      provider: values.provider,
      agent_mode: values.agentMode,
      username: values.username || 'spectre',
      hostname: values.hostname || 'kali',
      terminalId: firstTermId
    });

    setTimeout(() => setIsInitializing(false), 5000);
  };

  const sendCommand = (termId: string) => {
    const term = terminals.find(t => t.id === termId);
    if (!term || !socket) return;
    const trimmed = term.command.trim();
    if (!trimmed) return;

    updateTerminal(termId, {
      command: '',
      history: [...term.history, trimmed],
      historyIndex: -1
    });

    socket.emit('command', { cmd: trimmed, terminalId: termId });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, termId: string) => {
    const term = terminals.find(t => t.id === termId);
    if (!term) return;

    if (e.key === 'Enter') {
      sendCommand(termId);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (term.historyIndex < term.history.length - 1) {
        const newIndex = term.historyIndex + 1;
        updateTerminal(termId, {
          historyIndex: newIndex,
          command: term.history[term.history.length - 1 - newIndex]
        });
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (term.historyIndex > 0) {
        const newIndex = term.historyIndex - 1;
        updateTerminal(termId, {
          historyIndex: newIndex,
          command: term.history[term.history.length - 1 - newIndex]
        });
      } else {
        updateTerminal(termId, { historyIndex: -1, command: '' });
      }
    }
  };

  const toggleAgentMode = (checked: boolean) => {
    setAgentMode(checked);
    if (socket) {
      socket.emit('toggle_agent_mode', { enabled: checked });
    }
  };

  return (
    <ConfigProvider theme={{ algorithm: theme.darkAlgorithm, token: { colorPrimary: '#7c3aed', borderRadius: 8 } }}>
      {/* Complete OS Desktop Background */}
      <div style={{
        height: '100vh',
        width: '100vw',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)',
        position: 'relative',
        overflow: 'hidden',
        fontFamily: "'Inter', sans-serif"
      }}>

        {/* Top OS Menu Bar */}
        <div style={{
          height: '28px',
          background: 'rgba(15, 23, 42, 0.6)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0 16px',
          fontSize: '13px',
          color: '#e2e8f0',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 1000
        }}>
          <Space size="middle">
            <SafetyOutlined style={{ color: '#8b5cf6' }} />
            <Text style={{ fontWeight: 600, color: '#f8fafc' }}>SpectreOS</Text>
            <Text type="secondary" style={{ color: '#94a3b8' }}>Agent Workstation</Text>
          </Space>

          <Space size="middle">
            {isAuthenticated && (
              <>
                <Space>
                  <GlobalOutlined style={{ color: torStatus.status === 'Off' ? '#ef4444' : '#10b981' }} />
                  {torStatus.status === 'Off' ? (
                    <Text style={{ color: '#94a3b8', fontSize: '12px' }}>Tor Offline</Text>
                  ) : (
                    <Text style={{ color: '#10b981', fontSize: '12px' }}>{torStatus.ip} ({torStatus.status})</Text>
                  )}
                  <Switch
                    size="small"
                    checked={torStatus.status !== 'Off'}
                    onChange={(checked) => socket?.emit('command', { cmd: checked ? 'toron' : 'toroff' })}
                  />
                  <Text style={{ color: '#94a3b8', fontSize: '12px', marginRight: 8 }}>Tor</Text>
                </Space>
                <Space style={{ marginLeft: 8 }}>
                  {agentMode ? <RobotOutlined style={{ color: '#8b5cf6' }} /> : <CodeOutlined style={{ color: '#f59e0b' }} />}
                  <Switch
                    size="small"
                    checked={agentMode}
                    onChange={toggleAgentMode}
                  />
                  <Text style={{ color: '#94a3b8', fontSize: '12px' }}>{agentMode ? 'Agent' : 'Shell'}</Text>
                </Space>
                <div style={{ width: '1px', height: '14px', background: 'rgba(255,255,255,0.2)', margin: '0 8px' }} />
                <Tooltip title="System Logs & Debugger">
                  <div
                    onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                  >
                    <CodeOutlined style={{ color: isSidebarOpen ? '#7c3aed' : '#94a3b8', fontSize: '16px', transition: 'color 0.2s' }} />
                  </div>
                </Tooltip>
              </>
            )}
            <Text style={{ color: '#94a3b8', marginLeft: 16 }}>{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</Text>
          </Space>
        </div>

        {/* System Logging Sidebar */}
        <div style={{
          position: 'absolute',
          top: 28, // Below top menu
          left: 0,
          bottom: 0,
          width: isSidebarOpen ? '320px' : '0px',
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(20px)',
          borderRight: isSidebarOpen ? '1px solid rgba(255, 255, 255, 0.1)' : 'none',
          boxShadow: isSidebarOpen ? '10px 0 30px -10px rgba(0, 0, 0, 0.5)' : 'none',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          zIndex: 900,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          {/* Sidebar Header */}
          <div style={{
            height: '48px',
            minHeight: '48px',
            background: 'rgba(15, 23, 42, 0.9)',
            borderBottom: '1px solid rgba(255,255,255,0.05)',
            display: 'flex',
            alignItems: 'center',
            padding: '0 20px',
            justifyContent: 'space-between'
          }}>
            <Title level={5} style={{ margin: 0, color: '#f8fafc', whiteSpace: 'nowrap' }}>
              System Logs
            </Title>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ef4444', cursor: 'pointer' }} onClick={() => setIsSidebarOpen(false)} />
          </div>

          {/* Logs Body */}
          <div
            ref={sidebarScrollRef}
            style={{
              flex: 1,
              padding: '16px',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}
          >
            {systemLogs.length === 0 ? (
              <Text style={{ color: '#64748b', textAlign: 'center', marginTop: '20px' }}>No system events emitted.</Text>
            ) : (
              systemLogs.map(log => {
                let color = '#94a3b8'; // info
                if (log.level === 'error') color = '#ef4444';
                if (log.level === 'warning') color = '#f59e0b';
                if (log.level === 'success') color = '#10b981';

                return (
                  <div key={log.id} style={{
                    background: 'rgba(0, 0, 0, 0.3)',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    borderLeft: `3px solid ${color}`
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <Text style={{ fontSize: '11px', color: color, fontWeight: 600, textTransform: 'uppercase' }}>
                        {log.source}
                      </Text>
                      <Text style={{ fontSize: '11px', color: '#64748b' }}>
                        {log.timestamp}
                      </Text>
                    </div>
                    <Text style={{ fontSize: '12px', color: '#e2e8f0', wordBreak: 'break-word', fontFamily: "'Fira Code', monospace" }}>
                      {log.message}
                    </Text>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Render Window Manager Terminals */}
        {terminals.map((term, index) => {
          if (term.isMinimized) return null;

          // Slight cascading offset for multiple unmaximized windows
          const cascadeOffset = (index % 5) * 30;

          return (
            <div
              key={term.id}
              onClick={() => focusTerminal(term.id)}
              style={{
                position: 'absolute',
                top: term.isMaximized ? 28 : `calc(5% + ${cascadeOffset}px)`,
                left: term.isMaximized ? 0 : `calc(10% + ${cascadeOffset}px)`,
                right: term.isMaximized ? 0 : '10%',
                bottom: term.isMaximized ? 0 : '12%',
                background: 'rgba(17, 24, 39, 0.90)',
                backdropFilter: 'blur(25px)',
                borderRadius: term.isMaximized ? '0' : '12px',
                border: activeWindowId === term.id ? '1px solid rgba(124, 58, 237, 0.5)' : '1px solid rgba(255,255,255,0.1)',
                boxShadow: activeWindowId === term.id ? '0 25px 50px -12px rgba(0, 0, 0, 0.7)' : '0 20px 40px -15px rgba(0,0,0,0.4)',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                zIndex: term.zIndex,
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)'
              }}
            >
              {/* OSX Window Header */}
              <div style={{
                height: '38px',
                background: activeWindowId === term.id ? 'linear-gradient(to bottom, #334155, #1e293b)' : '#1e293b',
                borderBottom: '1px solid #0f172a',
                display: 'flex',
                alignItems: 'center',
                padding: '0 16px',
                justifyContent: 'space-between',
                cursor: 'default'
              }}>
                <Space size={8}>
                  <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ef4444', cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); closeTerminal(term.id); }} />
                  <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#f59e0b', cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); updateTerminal(term.id, { isMinimized: true }); }} />
                  <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#10b981', cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); updateTerminal(term.id, { isMaximized: !term.isMaximized }); }} />
                </Space>
                <Text style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)', fontWeight: 600, color: activeWindowId === term.id ? '#cbd5e1' : '#64748b', fontSize: '13px' }}>
                  {username}@{hostname}: ~
                </Text>
                <div />
              </div>

              {/* Terminal Body */}
              <div
                id={`term-scroll-${term.id}`}
                style={{
                  flex: 1,
                  padding: '20px',
                  overflowY: 'auto',
                  fontFamily: "'Fira Code', 'Courier New', monospace",
                  fontSize: '14px',
                  lineHeight: 1.6,
                  wordWrap: 'break-word',
                  whiteSpace: 'pre-wrap',
                  background: '#0a0a0a'
                }}
              >
                {outputs.filter(line => line.terminalId === term.id || !line.terminalId || line.terminalId === '_broadcast').map((line, idx) => (
                  <span key={idx} style={{ color: line.color || '#e2e8f0' }}>
                    {line.text.replace(/\r\n/g, '\n')}
                  </span>
                ))}
              </div>

              {/* Terminal Input */}
              <div style={{
                padding: '12px 20px',
                background: 'rgba(15, 23, 42, 0.95)',
                borderTop: '1px solid #1e293b',
                display: 'flex',
                gap: '12px',
                alignItems: 'center'
              }}>
                <Text strong style={{ color: '#8b5cf6', fontFamily: "'Fira Code', monospace" }}>
                  ┌──({username}㉿{hostname})-[~]
                  <br />└─$
                </Text>
                <Input
                  value={term.command}
                  onChange={(e) => updateTerminal(term.id, { command: e.target.value })}
                  onKeyDown={(e) => handleKeyDown(e, term.id)}
                  placeholder="Enter command or intent..."
                  style={{ flex: 1, fontFamily: "'Fira Code', monospace", fontSize: '14px', background: 'transparent' }}
                  bordered={false}
                  autoFocus={activeWindowId === term.id}
                />
                <Button type="primary" icon={<SendOutlined />} onClick={() => sendCommand(term.id)} size="large" style={{ background: '#7c3aed' }}>
                  Send
                </Button>
              </div>
            </div>
          )
        })}

        {/* OS Settings Modal (Always centered physically instead of pure Antd Modal for overlay look) */}
        {!isAuthenticated && isSettingsOpen && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: '450px',
            background: 'rgba(30, 41, 59, 0.85)',
            backdropFilter: 'blur(24px)',
            borderRadius: '16px',
            border: '1px solid rgba(255,255,255,0.1)',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
            overflow: 'hidden',
            zIndex: 50
          }}>
            <div style={{
              height: '48px',
              background: 'rgba(15, 23, 42, 0.6)',
              borderBottom: '1px solid rgba(255,255,255,0.05)',
              display: 'flex',
              alignItems: 'center',
              padding: '0 20px',
              justifyContent: 'space-between'
            }}>
              <Title level={5} style={{ margin: 0, color: '#f8fafc', display: 'flex', alignItems: 'center' }}>
                <SettingOutlined style={{ marginRight: 8, color: '#8b5cf6' }} />
                System Configuration
              </Title>
              {isAuthenticated && (
                <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ef4444', cursor: 'pointer' }} onClick={() => setIsSettingsOpen(false)} />
              )}
            </div>

            <div style={{ padding: '30px' }}>
              <Form layout="vertical" onFinish={handleInit} initialValues={{ provider: 'gemini', agentMode: true, username: 'spectre', hostname: 'kali' }}>
                <Space style={{ display: 'flex' }} size="large" align="start">
                  <Form.Item label={<Text style={{ color: '#cbd5e1' }}>Username</Text>} name="username" style={{ flex: 1 }}>
                    <Input size="large" placeholder="spectre" />
                  </Form.Item>
                  <Form.Item label={<Text style={{ color: '#cbd5e1' }}>Hostname</Text>} name="hostname" style={{ flex: 1 }}>
                    <Input size="large" placeholder="kali" />
                  </Form.Item>
                </Space>

                <Form.Item label={<Text style={{ color: '#cbd5e1' }}>Intelligence Provider</Text>} name="provider">
                  <Select size="large">
                    <Select.Option value="gemini">Google Gemini 2.0</Select.Option>
                    <Select.Option value="openai">OpenAI GPT-4o</Select.Option>
                    <Select.Option value="groq">Groq Llama 3</Select.Option>
                  </Select>
                </Form.Item>

                <Form.Item label={<Text style={{ color: '#cbd5e1' }}>Provider API Key</Text>} name="apiKey">
                  <Input.Password size="large" placeholder="Enter API Key to link models..." />
                </Form.Item>

                <Form.Item name="agentMode" valuePropName="checked">
                  <div style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text style={{ color: '#f8fafc', fontWeight: 500 }}>Global Agent Mode</Text>
                      <Switch checkedChildren="ON" unCheckedChildren="OFF" defaultChecked />
                    </div>
                    <Text type="secondary" style={{ fontSize: '12px', marginTop: '8px', display: 'block' }}>
                      If disabled, commands map directly to Kali Linux shell tools.
                    </Text>
                  </div>
                </Form.Item>

                <Form.Item style={{ marginBottom: 0, marginTop: 30 }}>
                  <Button type="primary" htmlType="submit" block loading={isInitializing} size="large" style={{ height: '48px', fontWeight: 600, fontSize: '16px', background: '#7c3aed' }}>
                    Connect Workstation
                  </Button>
                </Form.Item>
              </Form>
            </div>
          </div>
        )}

        {/* XFCE-Style OS Taskbar */}
        <div style={{
          position: 'absolute',
          top: '28px',
          left: 0,
          right: 0,
          height: '40px',
          background: 'rgba(15, 23, 42, 0.95)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 12px',
          gap: '8px',
          zIndex: 950,
          overflowX: 'auto',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)'
        }}>
          {/* Start Menu Placeholder / New Terminal Button */}
          <Tooltip title="Spawn New Terminal" placement="bottom">
            <Button
              type="text"
              icon={<DesktopOutlined style={{ color: '#8b5cf6' }} />}
              onClick={spawnTerminal}
              style={{
                background: 'rgba(124, 58, 237, 0.1)',
                border: '1px solid rgba(124, 58, 237, 0.3)',
                color: '#e2e8f0',
                fontWeight: 500,
                marginRight: '8px'
              }}
            >
              Terminal
            </Button>
          </Tooltip>

          <Tooltip title="System Configuration" placement="bottom">
            <Button
              type="text"
              icon={<SettingOutlined style={{ color: '#94a3b8' }} />}
              onClick={() => setIsSettingsOpen(!isSettingsOpen)}
              style={{
                color: '#94a3b8',
                marginRight: '8px'
              }}
            />
          </Tooltip>

          <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.1)', margin: '0 8px' }} />

          {/* Open Window Tabs */}
          {terminals.map((t, index) => {
            const isActive = activeWindowId === t.id && !t.isMinimized;
            return (
              <div
                key={t.id}
                onClick={() => {
                  if (t.isMinimized) {
                    updateTerminal(t.id, { isMinimized: false });
                  }
                  focusTerminal(t.id);
                }}
                style={{
                  height: '28px',
                  padding: '0 12px',
                  background: isActive ? 'rgba(124, 58, 237, 0.2)' : 'rgba(255,255,255,0.03)',
                  border: isActive ? '1px solid rgba(124, 58, 237, 0.5)' : '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  minWidth: '140px',
                  maxWidth: '200px'
                }}
              >
                <CodeOutlined style={{ color: isActive ? '#a78bfa' : '#64748b', fontSize: '12px' }} />
                <Text ellipsis style={{ color: isActive ? '#f8fafc' : '#94a3b8', fontSize: '12px', flex: 1, userSelect: 'none' }}>
                  Terminal {index + 1} {t.isMinimized ? '(Min)' : ''}
                </Text>
                <div
                  onClick={(e) => { e.stopPropagation(); closeTerminal(t.id); }}
                  style={{
                    width: '16px',
                    height: '16px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'rgba(239, 68, 68, 0.1)',
                    color: '#ef4444',
                    fontSize: '10px'
                  }}
                >
                  ✕
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </ConfigProvider>
  );
};

export default App;

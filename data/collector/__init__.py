"""data.collector：数据采集层。

包含三类采集客户端：
- opcua_client：DCS/PLC 工艺参数（OPC UA，asyncua）
- modbus_client：设备状态（电机电流/轴承温度/振动，pymodbus）
- rtsp_capture：视频监控流（RTSP，供视觉AI推理消费）
"""

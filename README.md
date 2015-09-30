# RealTimeExportServer
Export real-time pixel data from a Siemens MR scanner via TCP.

The server will listen on port 667 for data in the following format:

`[uint32 headerSize][uint32 dataSize][char header[headerSize]][short in data[dataSize/sizeof(short int)]] [4 Byte][4 Byte][headerSize][dataSize]`

* if headerSize > 0 and dataSize == 0:
  * Only big header is sent (first data that is available, which includes the protocol name to generate the filename)

* if headerSize == 0 and dataSize == 0:
  * MRI asks to close the connection, both zeros (uint32) will be sent back to the client

* else:
  * Store data to disk using filename defined from first big header (`meas_MID{MID}_{ProtocolName}.dat`)

#############################################################
# SmartLithium_BT

Acknowledgements to: 
    kwindrem - for SetupHelper and applications that demonstrate it's use for installing apps to Victron Cerbo
    

This is a project to retrieve the battery information
sent by Victron SmartLithium Batteries in BLE advertisements
and store it in the Cerbo for reporting to VRM and alerting

Hurdles in the project
    BLE advertisements are encrypted - decryption using AES-CTR
        is challenging as the encryption IV was done using little endian.  For now we can manually flip the IV bytes and decrypt.  
        If longer advertisements come later ( > 16 Byte block size of AES).  A new decryption will be necessary


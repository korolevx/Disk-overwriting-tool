# **Disk Overwriting Tool - Detailed Description**  

## **Overview**  
The **Disk Overwriting Tool** is a graphical Linux utility written in Python that securely overwrites disks, ensuring data is permanently erased. It supports multiple overwriting methods, including **single-pass zero-fill**, **DoD standard (3 passes)**, and the **Gutmann method (35 passes)**, as well as allowing a custom number of passes.  

The tool was developed using **GTK 3** for the graphical interface and requires **root permissions** to access and write directly to storage devices.  

---

## **Key Features**  
✅ **Device Selection** – Lists all available disks on the system.  
✅ **Multiple Overwrite Methods** – Offers different security levels:  
   - **Single Pass (Zeros)** – Fast but less secure.  
   - **DoD Standard (3 Passes)** – Balanced between speed and security.  
   - **Gutmann Method (35 Passes)** – Extremely secure but slow.  
   - **Custom Passes** – Allows specifying a custom number of passes.  
✅ **Real-Time Monitoring** – Displays progress, write speed, and estimated time remaining.  
✅ **Error Protection** – Checks if the disk is mounted or read-only before starting.  
✅ **Safe Cancellation** – Allows stopping the process at any time.  

---

## **Requirements and Dependencies**  
To run the **Disk Overwriting Tool**, the following packages must be installed on the system:  

### **System Dependencies (Ubuntu/Debian)**  
```bash
sudo apt update  
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 lsblk util-linux coreutils  
```  

### **Required Python Libraries**  
- `gi` (GObject Introspection) – For GTK interface  
- `subprocess` – For executing system commands (`lsblk`, `blockdev`)  
- `threading` – For background execution without freezing the interface  

---

## **How to Use**  
1. **Run as root** (required for direct disk access):  
   ```bash  
   sudo python3 diskoverwriter.py  
   ```  
2. **Select the disk** you want to overwrite.  
3. **Choose the method** (Zeros, DoD, Gutmann, or custom).  
4. **Click "Start Secure Erase"** and confirm the action.  
5. **Monitor progress** in the interface.  

---

## **Important Notes**  
⚠ **Data will be permanently lost!** Recovery is impossible after overwriting.  
⚠ **Always double-check the selected disk** before confirming.  
⚠ **SSDs may behave differently** due to wear leveling.

import configparser
import os

def create_camera_config():
    config = configparser.ConfigParser()
    
    # Default Configuration
    config["DEFAULT"] = {
        "framesize": "FRAME_SVGA",      # framesize: 800x600
        "pixformat": "JPEG",           # format
        "quality": "10",               # quality (0-63)
        "brightness": "0",             # brightness (-2 to 2)
        "contrast": "0",               # contrast (-2 to 2)
        "saturation": "0",             # saturation (-2 to 2)
    }
    
    # High quality mode configuration
    config["high_quality"] = {
        "framesize": "FRAME_UXGA",     # highest framesize 1600x1200
        "quality": "8",                # higher quality
        "brightness": "1",             # lighter
        "contrast": "1",               # more contrast
    }

    # Low quality mode for fast streaming
    config["low_quality"] = {
        "framesize": "FRAME_VGA",      # 640x480
        "quality": "15",               # lower quality
        "brightness": "0",
    }

    return config

def setup_camera_config():
    "Create and validate camera configuration"
    config = create_camera_config()
    
    # save file
    config_filename = 'camera_config.ini'
    with open(config_filename, 'w') as configfile:
        config.write(configfile)
    
    # check if the file created
    if os.path.exists(config_filename):
        print(f" Camera configuration file has been generated: {config_filename}")
        print(" Available configuration modes:", list(config.keys()))
        return True
    else:
        print("Configuration file creation failed")
        return False

def load_camera_config(mode='DEFAULT'):
    """
    Load camera configuration for specific mode
    """
    if not os.path.exists('camera_config.ini'):
        print("Please run setup_camera_config() first")
        return None
    
    config = configparser.ConfigParser()
    config.read('camera_config.ini')
    
    if mode not in config:
        print(f"Mode '{mode}' not found, using DEFAULT")
        mode = 'DEFAULT'
    
    return dict(config[mode])

# example
if __name__ == "__main__":
    setup_camera_config()
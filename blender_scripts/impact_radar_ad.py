"""
Impact Radar - 3D Advertisement Scene Setup Script
Run this in Blender's Scripting tab to auto-generate the entire ad scene.

How to use:
1. Open Blender
2. Go to "Scripting" tab (top menu bar)
3. Click "New" to create a new script
4. Paste this entire script
5. Update the SCREENSHOT_PATHS below with your actual file paths
6. Click "Run Script" (or press Alt+P)
"""

import bpy
import math
import os

# =============================================================================
# CONFIGURATION - Update these paths to your screenshot files
# =============================================================================

SCREENSHOT_PATHS = [
    "/path/to/dashboard_screenshot.png",      # Main dashboard
    "/path/to/trade_signals_screenshot.png",  # Trade signals
    "/path/to/events_screenshot.png",         # Events view
    "/path/to/playbook_screenshot.png",       # Playbook card
]

# Colors (hex to RGB normalized)
DARK_NAVY = (0.039, 0.039, 0.102, 1.0)  # #0a0a1a
NEON_CYAN = (0.0, 1.0, 1.0, 1.0)        # #00ffff
NEON_MAGENTA = (1.0, 0.0, 1.0, 1.0)     # #ff00ff

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def clear_scene():
    """Delete all objects in the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def setup_render_settings():
    """Configure Cycles renderer and output settings"""
    scene = bpy.context.scene
    
    # Set render engine to Cycles
    scene.render.engine = 'CYCLES'
    
    # Use GPU if available
    cycles_prefs = bpy.context.preferences.addons['cycles'].preferences
    cycles_prefs.compute_device_type = 'CUDA'  # or 'OPTIX', 'HIP', 'METAL'
    cycles_prefs.get_devices()
    for device in cycles_prefs.devices:
        device.use = True
    scene.cycles.device = 'GPU'
    
    # Render settings
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 250
    
    # Samples (adjust for quality vs speed)
    scene.cycles.samples = 128
    scene.cycles.preview_samples = 32
    
    # Output settings
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'HIGH'

def setup_world_background():
    """Set dark navy background with optional volumetrics"""
    world = bpy.data.worlds.get("World")
    if not world:
        world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    
    world.use_nodes = True
    nodes = world.node_tree.nodes
    nodes.clear()
    
    # Background node
    bg_node = nodes.new('ShaderNodeBackground')
    bg_node.inputs['Color'].default_value = DARK_NAVY
    bg_node.inputs['Strength'].default_value = 1.0
    bg_node.location = (0, 0)
    
    # Output node
    output_node = nodes.new('ShaderNodeOutputWorld')
    output_node.location = (200, 0)
    
    # Link nodes
    world.node_tree.links.new(bg_node.outputs['Background'], output_node.inputs['Surface'])
    
    # Optional: Add volume for fog effect
    volume_node = nodes.new('ShaderNodeVolumeScatter')
    volume_node.inputs['Color'].default_value = (0.1, 0.1, 0.2, 1.0)
    volume_node.inputs['Density'].default_value = 0.01
    volume_node.location = (0, -150)
    world.node_tree.links.new(volume_node.outputs['Volume'], output_node.inputs['Volume'])

def create_emissive_material(name, image_path=None, emission_strength=2.0):
    """Create a glowing material with optional image texture"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Create nodes
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)
    
    emission = nodes.new('ShaderNodeEmission')
    emission.location = (200, 0)
    emission.inputs['Strength'].default_value = emission_strength
    
    if image_path and os.path.exists(image_path):
        # Image texture for screenshot
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.location = (0, 0)
        tex_node.image = bpy.data.images.load(image_path)
        links.new(tex_node.outputs['Color'], emission.inputs['Color'])
    else:
        # Solid color fallback (cyan glow)
        emission.inputs['Color'].default_value = NEON_CYAN
    
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    
    return mat

def create_ui_panel(name, location, rotation, scale, image_path=None):
    """Create a floating UI panel plane with glowing material"""
    # Create plane
    bpy.ops.mesh.primitive_plane_add(size=2, location=location, rotation=rotation)
    panel = bpy.context.active_object
    panel.name = name
    
    # Scale to 16:9 ratio
    panel.scale = (scale[0] * 1.78, scale[1], scale[2])
    
    # Apply emissive material
    mat = create_emissive_material(f"{name}_material", image_path, emission_strength=1.5)
    panel.data.materials.append(mat)
    
    return panel

def create_neon_accent_cube(name, location, scale, color=NEON_CYAN):
    """Create a small glowing accent cube"""
    bpy.ops.mesh.primitive_cube_add(size=0.1, location=location)
    cube = bpy.context.active_object
    cube.name = name
    cube.scale = scale
    
    # Add bevel modifier for rounded edges
    bevel = cube.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.02
    bevel.segments = 4
    
    # Create emissive material
    mat = bpy.data.materials.new(name=f"{name}_material")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    
    emission = nodes.new('ShaderNodeEmission')
    emission.location = (100, 0)
    emission.inputs['Color'].default_value = color
    emission.inputs['Strength'].default_value = 5.0
    
    mat.node_tree.links.new(emission.outputs['Emission'], output.inputs['Surface'])
    cube.data.materials.append(mat)
    
    return cube

def create_camera_with_animation():
    """Create and animate the camera in an orbit path"""
    # Create camera
    bpy.ops.object.camera_add(location=(0, -8, 2))
    camera = bpy.context.active_object
    camera.name = "AdCamera"
    
    # Set as active camera
    bpy.context.scene.camera = camera
    
    # Point camera at center
    camera.rotation_euler = (math.radians(80), 0, 0)
    
    # Enable depth of field
    camera.data.dof.use_dof = True
    camera.data.dof.aperture_fstop = 2.8
    
    # Animate camera orbit
    # Frame 1: Starting position
    bpy.context.scene.frame_set(1)
    camera.location = (0, -8, 2)
    camera.rotation_euler = (math.radians(80), 0, 0)
    camera.keyframe_insert(data_path="location", frame=1)
    camera.keyframe_insert(data_path="rotation_euler", frame=1)
    
    # Frame 80: Move right and up
    bpy.context.scene.frame_set(80)
    camera.location = (5, -6, 3)
    camera.rotation_euler = (math.radians(75), 0, math.radians(30))
    camera.keyframe_insert(data_path="location", frame=80)
    camera.keyframe_insert(data_path="rotation_euler", frame=80)
    
    # Frame 160: Move to left side
    bpy.context.scene.frame_set(160)
    camera.location = (-4, -5, 2.5)
    camera.rotation_euler = (math.radians(78), 0, math.radians(-25))
    camera.keyframe_insert(data_path="location", frame=160)
    camera.keyframe_insert(data_path="rotation_euler", frame=160)
    
    # Frame 250: Pull back for wide shot
    bpy.context.scene.frame_set(250)
    camera.location = (0, -10, 4)
    camera.rotation_euler = (math.radians(70), 0, 0)
    camera.keyframe_insert(data_path="location", frame=250)
    camera.keyframe_insert(data_path="rotation_euler", frame=250)
    
    # Smooth keyframe interpolation
    for fcurve in camera.animation_data.action.fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = 'BEZIER'
            keyframe.handle_left_type = 'AUTO_CLAMPED'
            keyframe.handle_right_type = 'AUTO_CLAMPED'
    
    return camera

def create_area_light(name, location, rotation, size=5, energy=100, color=(1, 1, 1)):
    """Create an area light for soft illumination"""
    bpy.ops.object.light_add(type='AREA', location=location, rotation=rotation)
    light = bpy.context.active_object
    light.name = name
    light.data.size = size
    light.data.energy = energy
    light.data.color = color[:3]
    return light

def create_floating_particles():
    """Create subtle floating particle effect"""
    # Create emitter object (invisible cube)
    bpy.ops.mesh.primitive_cube_add(size=10, location=(0, 0, 0))
    emitter = bpy.context.active_object
    emitter.name = "ParticleEmitter"
    emitter.hide_render = True
    
    # Add particle system
    bpy.ops.object.particle_system_add()
    ps = emitter.particle_systems[0]
    ps.name = "DataParticles"
    
    settings = ps.settings
    settings.count = 200
    settings.lifetime = 250
    settings.emit_from = 'VOLUME'
    settings.physics_type = 'NO'
    settings.render_type = 'OBJECT'
    settings.particle_size = 0.02
    
    # Create small glowing sphere for particles
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.02, location=(100, 100, 100))
    particle_obj = bpy.context.active_object
    particle_obj.name = "ParticleSphere"
    
    # Glowing material for particles
    mat = bpy.data.materials.new(name="ParticleMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    output = nodes.new('ShaderNodeOutputMaterial')
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (0.3, 0.5, 1.0, 1.0)  # Light blue
    emission.inputs['Strength'].default_value = 3.0
    mat.node_tree.links.new(emission.outputs['Emission'], output.inputs['Surface'])
    particle_obj.data.materials.append(mat)
    
    # Set particle render object
    settings.instance_object = particle_obj

def create_logo_plane(logo_path, location=(0, 0, 4)):
    """Create floating logo at the end"""
    if logo_path and os.path.exists(logo_path):
        bpy.ops.mesh.primitive_plane_add(size=2, location=location)
        logo = bpy.context.active_object
        logo.name = "Logo"
        
        mat = create_emissive_material("LogoMaterial", logo_path, emission_strength=3.0)
        logo.data.materials.append(mat)
        
        # Face camera
        logo.rotation_euler = (math.radians(90), 0, 0)
        
        return logo
    return None

# =============================================================================
# MAIN SCENE SETUP
# =============================================================================

def build_impact_radar_ad():
    """Main function to build the entire advertisement scene"""
    print("Building Impact Radar Advertisement Scene...")
    
    # Step 1: Clear and setup
    clear_scene()
    setup_render_settings()
    setup_world_background()
    
    # Step 2: Create UI panels (arrange in 3D space)
    panels = []
    
    # Main dashboard (center, slightly back)
    panel1 = create_ui_panel(
        "Dashboard",
        location=(0, 0, 0),
        rotation=(math.radians(10), 0, 0),
        scale=(1.5, 1.5, 1),
        image_path=SCREENSHOT_PATHS[0] if len(SCREENSHOT_PATHS) > 0 else None
    )
    panels.append(panel1)
    
    # Trade signals (right, angled)
    panel2 = create_ui_panel(
        "TradeSignals",
        location=(3.5, 1, -0.5),
        rotation=(math.radians(15), math.radians(-20), math.radians(-5)),
        scale=(1.0, 1.0, 1),
        image_path=SCREENSHOT_PATHS[1] if len(SCREENSHOT_PATHS) > 1 else None
    )
    panels.append(panel2)
    
    # Events (left, angled)
    panel3 = create_ui_panel(
        "Events",
        location=(-3.5, 1, -0.3),
        rotation=(math.radians(12), math.radians(20), math.radians(5)),
        scale=(1.0, 1.0, 1),
        image_path=SCREENSHOT_PATHS[2] if len(SCREENSHOT_PATHS) > 2 else None
    )
    panels.append(panel3)
    
    # Playbook (top right, smaller)
    panel4 = create_ui_panel(
        "Playbook",
        location=(2.5, 2, 1.5),
        rotation=(math.radians(5), math.radians(-10), 0),
        scale=(0.7, 0.7, 1),
        image_path=SCREENSHOT_PATHS[3] if len(SCREENSHOT_PATHS) > 3 else None
    )
    panels.append(panel4)
    
    # Step 3: Add neon accent elements
    create_neon_accent_cube("AccentCube1", location=(-2, -1, -1), scale=(0.5, 0.5, 0.1), color=NEON_CYAN)
    create_neon_accent_cube("AccentCube2", location=(2.5, 0, 1.2), scale=(0.3, 0.3, 0.05), color=NEON_MAGENTA)
    create_neon_accent_cube("AccentCube3", location=(-1.5, 1.5, 0.8), scale=(0.2, 0.4, 0.05), color=NEON_CYAN)
    
    # Step 4: Create camera with animation
    camera = create_camera_with_animation()
    
    # Set DOF focus to main dashboard
    camera.data.dof.focus_object = panels[0]
    
    # Step 5: Add lighting
    create_area_light("KeyLight", location=(3, -5, 5), rotation=(math.radians(60), 0, math.radians(30)), 
                     size=4, energy=50, color=(0.9, 0.95, 1.0))
    create_area_light("FillLight", location=(-4, -3, 3), rotation=(math.radians(45), 0, math.radians(-30)),
                     size=3, energy=20, color=(0.7, 0.8, 1.0))
    create_area_light("RimLight", location=(0, 5, 2), rotation=(math.radians(-30), 0, 0),
                     size=5, energy=30, color=(0.5, 0.6, 1.0))
    
    # Step 6: Add floating particles (optional - comment out if too slow)
    # create_floating_particles()
    
    # Reset to frame 1
    bpy.context.scene.frame_set(1)
    
    print("Scene setup complete!")
    print("Next steps:")
    print("1. Update SCREENSHOT_PATHS at the top of this script with your actual image paths")
    print("2. Run the script again if you updated paths")
    print("3. Press Numpad 0 to view through the camera")
    print("4. Press Space to play the animation")
    print("5. Render with Ctrl+F12 when ready")

# =============================================================================
# RUN THE SCRIPT
# =============================================================================

if __name__ == "__main__":
    build_impact_radar_ad()

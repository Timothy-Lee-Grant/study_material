# Windows Internals, Part 6: Device Stacks, Plug and Play, INF Files, and Driver Signing (audio lecture)

This is part six of an eight-part series on Windows internals. Part five covered interrupt handling. This part covers how Windows organizes drivers around each device: the device tree, device stacks with their physical, functional and filter layers, how Plug and Play builds them, how an installation file picks a driver, and why kernel drivers must be signed.

## Why this episode exists

Every device investigation ends up on the same map: which drivers are layered on this device, who created each layer, how the device got that driver, and why Windows trusted it. Timothy has seen pieces of this map: the touchscreen's A-C-P-I layer, the HID class driver, the separate I2C and G-P-I-O controller stacks. This episode builds the map from the bottom up, so he can place any driver on it and say who owns what.

## The core ideas

Here are today's core ideas. They're the answer key for the walk questions at the end.

One. The device tree records which devices exist and how they're connected, parent to child. Each device in the tree has a device stack: the drivers layered on that one device.

Two. A stack has three kinds of layer. At the bottom, the physical device object, P-D-O, created by the bus driver that discovered the device. Above it, the functional device object, F-D-O, created by the function driver that runs the device. And optional filter layers above or below the function driver.

Three. The tree grows by enumeration: a bus driver reports its children, Plug and Play finds and loads each child's drivers, each driver attaches its layer, then Plug and Play assigns the device's resources and sends start.

Four. Requests travel down a stack as input-output request packets, I-R-Ps. Each layer completes a request, passes it down, or holds it. The layer holding a stuck request owns the problem.

Five. An INF file is the installation recipe. It says which hardware identifiers a driver supports, which files to copy, and how to register the driver as a kernel service. Windows ranks matching INF files and installs the best one from its driver store.

Six. Kernel drivers must be signed, because kernel code is trusted with everything. Production drivers are tested and signed through Microsoft's hardware compatibility program. Attestation signing exists for client Windows without that testing. Test signing works only on machines put into test mode.

## Section one: three structures

The kernel keeps three structures here, and it helps to know what each stands for.

A driver object exists once per loaded driver. It represents the driver's code: its table of request handlers and callbacks.

A device object exists once per device, per driver layer. It represents one driver's role on one device, and it holds that driver's private state for that device, in an area called the device extension.

A device node, or dev-node, exists once per device. It's the Plug and Play manager's record of the device itself: its identity, its parent and children in the tree, its state, its problem code if any, and its hardware resources.

One driver object can own many device objects: one driver running three identical sensors. And one device has several device objects, one per driver layered on it.

## Section two: the layers of a stack

Picture a device stack from the bottom up.

At the bottom is the physical device object, the P-D-O. The bus driver of the parent bus created it, whether that's A-C-P-I, P-C-I, a U-S-B hub, or the HID class driver for HID collections. The bus driver knows the device exists on its bus: it reports the device's identity and resources, and it controls the device's power on that bus.

Above it is the functional device object, the F-D-O, created by the function driver: the main driver that knows the device's own registers, protocol and behavior.

Filters can sit above the function driver (upper filters) or below it (lower filters). A filter adds, changes or observes requests passing through, for logging, for fixing quirks, or for a vendor's extra features.

Two details matter. First, one driver can play different roles in different stacks. The HID class driver is the function driver for a HID-over-I2C touch device, and it's also the bus driver that creates physical device objects for each HID collection it finds inside that device, like a touch digitizer and a pen. Second, filters don't decide on their own where to attach. Registry settings installed by an INF file put them there. That's how a vendor's filter can quietly sit in a stack you didn't expect, and bang-dev-stack in the debugger will show it.

## Section three: how stacks get built

There are two phases: setup time and run time.

At setup time, here's the sequence. The A-C-P-I driver loads early and reads the firmware's tables. The Plug and Play manager asks it for its children, and it answers with a physical device object for each device the tables describe: the touchscreen, the I2C controller, the G-P-I-O controller. For each new child, Plug and Play creates a dev-node and asks for the child's hardware identifiers. It matches those against INF files in the driver store and installs the best match if needed. It loads the stack's drivers: lower filters, the function driver, upper filters. Each driver's add-device routine creates its device object and attaches it on top. Then Plug and Play assigns resources, like memory ranges, interrupts, and I2C connections, which for an A-C-P-I device come from its firmware description, and sends a start request down the stack. In the framework, start becomes two callbacks: prepare-hardware, where the driver maps its registers and opens its bus connection, and D-zero-entry, where it powers up and initializes. And if the function driver has children of its own, like HID collections, the same steps repeat one level down.

At run time, the stacks just exist, and requests flow through them. Plug and Play only steps in again for changes: removal, a device disappearing suddenly, disable and enable, or a driver update. Disable and enable, in these terms, means: remove the whole stack, then rebuild it from the loading step. That's why it clears stuck driver state, and why it destroys evidence.

Problem codes record where this sequence failed. Code twenty-eight means no driver was installed. Codes thirty-one and thirty-nine mean the driver couldn't be loaded. Code ten means the device couldn't start, often because hardware didn't respond or the resources were wrong. Code forty-three means the driver reported a problem after starting. Code fifty-two means the driver's signature was rejected.

## Section four: requests through a stack

An input-output request packet, an I-R-P, is the kernel's request object. It holds the request type (read, write, device control, Plug and Play, or power), the buffers, and one slot per layer for that layer's parameters. A request enters at the top. Each layer either completes it, passes it to the next layer down, or holds it to finish later, for example while waiting for hardware. When it's finally completed, layers that asked to be notified get a callback on the way back up.

In the debugger, bang-I-R-P lists the slots, and the one marked with an arrow is the layer holding it now. A request held forever by one driver is the root of many hangs and of the power-failure blue screen nine-F. The Kernel-Mode Driver Framework hides most of this: requests arrive as request objects in queues, and the framework handles the Plug and Play and power requests itself, turning them into callbacks.

## Section five: the touchscreen, fully mapped

Here's the full map for a laptop touchscreen. A-C-P-I is the root bus. Under it in the tree are three siblings: the I2C controller, the G-P-I-O controller, and the HID-over-I2C touch device. Each has its own stack, with an A-C-P-I physical device object at the bottom. The I2C controller's function driver is the chip vendor's, built on the framework extension for simple peripheral buses. The G-P-I-O controller's is the chip vendor's too, built on the G-P-I-O framework extension. The touch device's function driver is the HID class driver, with the HID-over-I2C mini-driver plugged into it. Under the touch device in the tree are its HID collections, like the digitizer, each with a physical device object created by the HID class driver, and the input drivers above that.

Two runtime links aren't parent and child at all. The HID-over-I2C driver sends read requests to the I2C controller's stack through a connection resource. And the touch controller's pin on the G-P-I-O controller is routed as an interrupt to the HID-over-I2C driver's interrupt routine.

So when touch input stops, four stacks could be involved: the touch device's own stack, the I2C controller's for the transfers, the G-P-I-O controller's for the interrupt routing, and the digitizer collection's stack for delivering input.

## Section six: hardware identifiers and choosing a driver

When a bus driver reports a device, it gives two ordered lists. Hardware identifiers come first, most specific first: an A-C-P-I identifier with a vendor and device code, for example. Compatible identifiers are generic class identities, like A-C-P-I backslash P-N-P-zero-C-fifty, which means HID over I2C. Other buses have their own formats. P-C-I uses a vendor number and device number. U-S-B uses a vendor I-D and product I-D. HID collections use vendor and product codes plus a collection number.

To choose, Plug and Play collects every INF in the driver store that matches any identifier, then ranks them. Better signature trust beats worse. A match on a hardware identifier beats a match on a compatible identifier, and a more specific identifier beats a less specific one. Then a newer date and version wins. That's how a generic touchscreen just works: Microsoft's built-in HID-over-I2C INF matches the compatible identifier. And a vendor can override it by shipping an INF that matches the more specific hardware identifier.

## Section seven: reading an INF file

An INF file is plain text organized into sections with names in square brackets. Here's the chain to follow when you read one.

The Version section identifies the file: its device class, its provider, the name of its signed catalog file, and its date and version, which matter for ranking. The Manufacturer section points to per-architecture model lists, decorated with a platform and a minimum Windows build, for example one list for sixty-four-bit Intel and another for Arm sixty-four. A model line is the actual match: it says "this device description, install with this section, for this hardware identifier". The install section says which files to copy. Its services subsection registers the driver as a kernel service and marks it as the function driver for the device. A framework subsection binds it to the Kernel-Mode Driver Framework. Filters are added by registry lines naming upper or lower filter services.

One bring-up lesson hides in those per-architecture model lists: if a driver package has no Arm sixty-four list, it won't install on an Arm laptop, however well it works on Intel.

Installing a package means checking its signature, copying the whole package into the driver store, and installing it on matching devices. The built-in tool pnputil does this from the command line: adding and installing a driver, listing driver packages, listing devices with problem codes, deleting a package, and restarting a device. Device Manager's details tab shows a field called "matching device I-D", which tells you which identifier the installed INF actually matched. That settles "why did it pick this driver?"

Pause and predict. Microsoft's generic HID-over-I2C driver is installed on a touchscreen, but the vendor's driver is in the store too. What would explain the generic one winning?

The vendor's INF might not match this device's identifiers at all: a typo in the hardware I-D, or no list for this architecture. Or the vendor's package might rank lower for signature trust. Checking the matching device I-D and the vendor INF's model lines would settle it.

## Section eight: driver signing

Why sign? Kernel-mode code runs with full privilege in the shared kernel address space. A tampered or malicious kernel driver can do anything. So Windows enforces kernel-mode code integrity: a kernel driver loads only if its signature chains to a trusted authority and its files match the signed hashes.

What's actually signed is the package's catalog file, which lists a cryptographic hash of every file in the package. Installing checks the catalog's signature, then each file's hash. Drivers that start during boot are usually also signed inside the driver file itself.

There are four signing paths. Hardware-compatibility signing means running Microsoft's Hardware Lab Kit tests, submitting the results, and having Microsoft sign; Microsoft calls it the recommended method because it signs for all Windows versions, and it's the path to Windows Update. Attestation signing means submitting the package through Microsoft's partner portal, which requires an extended-validation certificate, without the lab tests; Microsoft notes such drivers aren't Windows-certified, can't go to retail Windows Update, and work only on client Windows ten and later. Pre-production signing is for partners testing on Secure Boot machines provisioned to trust it. And test signing uses your own certificate, on machines put into test mode, which requires Secure Boot off and shows a watermark on the desktop.

Two more gates exist. Memory integrity, also called H-V-C-I, uses the hypervisor to enforce code integrity, and drivers must be compatible with it. And Microsoft keeps a block list of specific signed drivers known to be vulnerable. When signing goes wrong, the device shows code fifty-two, and the code integrity event log explains why.

## Connections

This connects to part one: bang-dev-node shows the tree and bang-dev-stack shows a stack. It connects to part two: in a nine-F, the arrow in bang-I-R-P names the layer holding the power request. And it connects to part seven: the physical device object's bus driver is the layer that actually switches a device's power.

## Recap

The core ideas once more. The tree says what exists; each device's stack says which drivers sit on it. Bus drivers create physical device objects, function drivers create functional device objects, and INF settings place filters. Plug and Play builds stacks by enumerating, matching, loading, attaching, assigning resources and starting, and problem codes record which step failed. Requests flow down stacks, and the holding layer owns a stuck one. INF files map identifiers to install steps, and Windows ranks matches by signature, specificity, then date. Kernel drivers must be signed: through hardware-compatibility testing for production, attestation for client Windows, or test signing in test mode.

## Walk questions

Three questions for the next walk.

First: who creates the physical device object, the functional device object, and filter layers, and what does each know?

Second: walk through the setup-time steps from a bus reporting a child to a started device stack, and name what problem codes ten, twenty-eight and fifty-two mean.

Third: compare hardware-compatibility signing and attestation signing.

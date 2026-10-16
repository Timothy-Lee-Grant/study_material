# Know It Exists, Part 2: Who Starts Your Code, and What Keeps It Going (audio lecture)

This is part two of a three-part series about concepts worth knowing just because they exist. Part one covered how programs find out that something happened. This part covers how work gets started, scheduled, and kept running. Part three covers storing, connecting, and checking.

## Why this matters

One of Timothy's own examples was the Linux background daemon. Once he knew that systemd reads a small unit file, starts a program, and restarts it if it dies, an always-running program became something he could design with. He uses this at work: his team's emulator runs each entry point as a systemd unit.

The daemon is one answer to a bigger question, and asking that question is a skill in itself: **who starts my code, and when?** An always-on daemon is one answer. There are at least six others, and each one opens up a different kind of system. A program that runs every night at two. A program that runs the moment a USB device is plugged in. A program that exists only for the half second it takes to handle a request. A workflow that pauses for three days waiting for a human to approve something, and survives a reboot in the middle. Without names for these, you end up building all of them as a daemon with a loop and a sleep, and fighting the result.

The card format from part one still applies. Each concept gets its smell (the moment in design that should bring it to mind), what it is in one sentence, where it lives and who calls whom, the catch, and the words to say to the AI.

## The core ideas

One. "Who starts this code, and when?" is a design decision with at least seven common answers: always on, on a schedule, on a hardware event, on a queued job, on a trigger in the cloud, as a durable workflow, or by a loop that keeps reality matching a declared goal.

Two. On a Linux machine you control, systemd timers are the modern replacement for cron. They log every run, can catch up on runs missed while the machine was off, and can wait for other services.

Three. Udev rules let the Linux kernel's device events trigger actions and give devices stable names, so "when this sensor is plugged in, start my service" is a configuration line, not a polling loop.

Four. A job queue hands slow or unreliable work to background workers, with automatic retries and a dashboard of what failed.

Five. A serverless function is code that exists only when a trigger fires. You pay per run and manage no machine, but the first run after a quiet period is slow, and runs are short.

Six. Durable execution lets ordinary-looking code survive crashes and wait for days, by recording every step and replaying the history. The price is that the workflow code must be deterministic.

Seven. Reconciliation means you declare the state you want, and a loop repeatedly compares it with reality and fixes the difference. This is how Kubernetes, Terraform, and Bicep work.

Eight. A lease is a lock with an expiry time, used so that only one machine does a job at a time. A fencing token protects against a machine that doesn't know its lease has run out.

Nine. Feature flags separate deploying code from turning it on.

## Section one: the question behind the daemon

Here's the smell that opens this whole episode. You catch yourself writing a loop like this in words: "while true, check whether it's time, or whether something needs doing, then sleep." Every time you see that loop, it's the program doing a job some other part of the system is designed to do for you: the operating system's scheduler, the kernel's device manager, a job queue, or a cloud platform's trigger system.

So before writing the loop, ask: what is the real event that should start this work? Is it a time of day, a device appearing, a request arriving, a message in a queue, or reality drifting from what it should be? Each one has a home.

## Section two: systemd timers, scheduling on a machine you own

The classic Linux scheduler is **cron**. A cron table has one line per job, and each line has five time fields (minute, hour, day of month, month, day of week) followed by a command. It's everywhere, and you'll see cron expressions in many cloud schedulers, so the five-field format is worth recognizing.

On a modern Linux system, especially one already using systemd like yours, the better tool is a **systemd timer**. You write two small files: a service unit that says what to run, and a timer unit that says when, with a line like "OnCalendar equals daily at two A M." The timer starts the service on schedule.

Why prefer it over cron? Three reasons. First, every run's output goes to the system journal, so "did last night's job fail, and why" has an answer. With cron, output often disappears. Second, a setting called Persistent means that if the machine was off at two A M, the job runs as soon as it boots. Plain cron simply skips missed runs. Third, the timer's service can depend on other services, so "only run the backup once the network and the database are up" is one line.

The smell: "this should happen every night, or every fifteen minutes, on this one machine." The catch: a timer schedules on *one* machine. If you run three copies of a service, all three timers fire, and that's a coordination problem, which section eight covers.

## Section three: udev rules, when hardware is the trigger

This one fits Timothy's embedded Linux work especially well. On Linux, when a device appears (a USB serial adapter, a sensor, a storage stick), the kernel sends an event, and a system service called **udev**, said "you-dev", decides what to do with it. You can add your own rules: small text files in a folder called udev rules dot d. A rule matches a device by attributes such as its vendor ID, product ID, or serial number, and then does something.

There are two especially useful actions. The first is giving the device a **stable name**. USB serial devices get names like tty-U-S-B-zero, and which number a device gets depends on plug-in order, so after a reboot your sensor might show up as one instead of zero. A udev rule can create a fixed name, say slash dev slash my-sensor, that always points to the right device. The second is **triggering work** when the device appears or disappears, such as starting a service.

The smell: "when this device is plugged in, start something", or "my program sometimes opens the wrong serial port after a reboot."

The catch: udev expects its rules to finish almost instantly and will kill long-running commands. So the correct pattern is for the rule to *ask systemd to start a service*, and the service does the long-running work. That's a nice example of these concepts fitting together: the device event comes from the kernel, the decision from udev, the running from systemd.

## Section four: job queues, handing work to the background

Part one introduced message queues as a way to move events between systems. A **job queue**, also called a background job system, is a more opinionated version aimed at one use: "run this function later, somewhere else, and retry it if it fails."

The smell: a web request triggers something slow or flaky, like sending an email, resizing an image, calling an AI model, or generating a report, and you don't want the user waiting or the request timing out. Or: work that must be retried with growing delays until it succeeds.

Here's how it works. Your code says, in effect, "enqueue a job: send the welcome email to user forty-two." That call returns immediately. The job is stored, usually in a database or Redis. Separate worker processes pick jobs up, run them, and on failure schedule a retry with **exponential backoff**: wait one second, then two, then four, then eight, so a struggling service isn't hammered. After too many failures the job is marked dead, and you see it in a dashboard. Most of these libraries also support scheduled and recurring jobs.

The names: in dot net, Hangfire is the best known. In Python, Celery. In Node, BullMQ. In Ruby, Sidekiq. Dot net's own BackgroundService, which Timothy has used, is the always-on worker *without* the persistence and retry machinery. Seeing that difference clearly is useful: a BackgroundService loses its in-memory work if the process restarts, and a job queue doesn't.

The catch is the one from part one: retries mean a job can run more than once, so jobs must be idempotent. Don't pass big objects into a job either. Pass an ID and let the job load fresh data, because the data may have changed by the time the job runs.

## Section five: serverless functions, code that exists only when triggered

So far all the code has run on a machine you manage. **Serverless functions** flip that around. You upload a function and tell the cloud platform what should trigger it: an HTTP request, a timer, a message on a queue, a file landing in storage, a database change. The platform starts the function when the trigger fires, runs it, and stops it afterwards. There's no server to maintain, it scales up automatically under load and down to zero when idle, and you pay per run.

The names: on Azure, **Azure Functions**, which is worth knowing well for the Microsoft path. On Amazon, Lambda. On Cloudflare, Workers. In Azure Functions the trigger types are called **bindings**, and they map directly onto part one: an HTTP trigger is a webhook receiver, a queue trigger is a consumer, a timer trigger is a cloud cron.

The smell: "this little piece of glue runs a few times a day when something happens, and I don't want to keep a server alive for it." Webhook receivers are a classic first serverless function.

The catches. First, **cold starts**: after a quiet period, the first request has to wait while the platform starts your code, which can take from a fraction of a second up to several seconds. Second, functions have time limits and keep no memory between runs, so anything that must persist goes into storage. Third, they can't reach hardware: anything touching a physical device stays on a machine you own.

## Section six: durable execution, code that survives crashes and waits for days

This is the most mind-expanding concept in this episode, and it connects directly to the state-machine work Timothy is doing with his senior engineer.

Here's the smell. A process has several steps that span a long time and must not lose its place: "charge the card, then reserve the stock, then wait up to three days for the warehouse to confirm, and if it never does, refund the card." Written naively, that's a nightmare. Where do you keep the fact that you're on step three? What if the server reboots on day two? People usually end up building a database table of statuses and a polling loop. That's a hand-built state machine, scattered across the codebase.

**Durable execution** lets you write that whole process as one ordinary-looking function, top to bottom, including a line that effectively says "wait three days for this event", and it just works, even across crashes and deployments.

Here's the mechanism, because it's what makes the catch make sense. The workflow engine records every step's result in a history log: "step one, charge card, returned success." If the machine dies, the engine starts the function again from the top on another machine, but it **replays** the history: when the code reaches "charge the card", the engine doesn't charge again. It hands back the recorded result instantly. The code fast-forwards through the history until it reaches the point where it left off, then continues for real. A three-day wait isn't a sleeping thread. The workflow is unloaded entirely, and a timer in the engine wakes it later.

The names: **Temporal**, the best known general-purpose engine. On Azure, **Durable Functions**, an extension of Azure Functions. On Amazon, Step Functions, which you describe as a state machine directly.

The catch follows from the replay. The workflow code must be **deterministic**: given the same history, it must make the same decisions every time. So inside the workflow you can't read the current time directly, generate random numbers, or call the network. Those things go in separate steps called **activities**, whose results get recorded. The engines provide replay-safe versions of "now" and "random." AI-written workflow code breaks this rule constantly, so knowing the rule exists is real review power.

Here's the connection to Timothy's current thinking. A durable workflow *is* a state machine. The engine stores the state and the history of transitions for you, and you write it as straight-line code.

Pause and predict: inside a durable workflow, you write "if the current time is after five P M, send it to the night queue." The workflow crashes and replays the next morning. What goes wrong? On replay, "current time" is now the morning, so the code takes a different branch than it did the first time, and the history no longer matches the code. The engine treats this as an error. That's why the time has to come from the engine's recorded clock.

## Section seven: reconciliation, declare what you want and let a loop converge

Most code is **imperative**: do this, then this, then this. **Reconciliation** is **declarative**: you write down the state you want, and a program called a controller repeatedly compares that desired state with the actual state and takes whatever action closes the gap.

Here's a simple example. You declare "three copies of this web service should be running." The controller looks and sees two, so it starts one. A machine dies and takes one copy with it, so the next time the loop runs it sees two again and starts another. You never wrote "if a machine dies, restart the service." You wrote what should be true, and the loop keeps making it true. That's called **self-healing**.

The names: **Kubernetes** is built entirely on this. Every Kubernetes object is a desired state, and controllers reconcile it. **Infrastructure as code** tools apply the same idea to cloud resources: **Terraform**, and on Azure, **Bicep**, said like the muscle. You write a file describing the virtual network, the database, and the storage account you want. The tool compares it with what exists in the cloud, shows you a plan of the changes, and applies them. Your infrastructure lives in version control, gets reviewed like code, and can be rebuilt from scratch.

The smell: "I keep setting this up by clicking around in a portal", or "after a failure, things need to get back to how they're supposed to be", or "I'm writing a long script of steps that breaks if any step was already done."

That last smell connects back to part one. Reconciliation is idempotent by design: applying the same desired state twice changes nothing the second time. That's exactly why it's so robust.

The catch: someone changes the real system by hand, the declared state no longer matches, and the next reconciliation silently undoes their change, or fights it. That mismatch is called **drift**. The rule is that once something is managed by declaration, all changes go through the declaration.

## Section eight: leases and leader election, only one at a time

Back to the catch from systemd timers. You run three copies of a service for reliability, and there's one job that must happen exactly once every night: sending the daily report. Three timers fire, and three reports go out. Or there's a hardware bus that only one process may drive at a time. The smell: "only one of these may do this at a time, across processes or machines."

On a single machine, you'd use a lock. Across machines, the concept is a **lease**: a lock with an expiry time, held in some shared place that all the copies can see, such as a database row, a blob in Azure Storage (which has built-in leases), Redis, or a coordination service like etcd, said "et-see-dee". A copy acquires the lease for, say, thirty seconds, does the work, and keeps renewing the lease while it's alive. If it crashes, it stops renewing, the lease expires, and another copy takes over. When the job is "be the one in charge" for a long time, this is called **leader election**.

Why an expiry? A lock without one, held by a machine that has died, stays locked forever.

The catch is subtle and well known. A machine holding the lease can freeze, say for a long garbage-collection pause or a network stall, for longer than the lease lasts. Meanwhile the lease expires and another machine takes over. Then the first machine wakes up, still believing it's in charge, and both act at once. The defense is a **fencing token**: every time the lease is granted, it comes with an increasing number, and the resource being protected rejects any request carrying a number older than the newest one it has seen. Martin Kleppmann's writing on distributed locks explains this well.

## Section nine: feature flags, deploying is not releasing

The last concept is small, and it changes how you ship. A **feature flag** is a switch the code checks at run time: "if the new shutdown algorithm is enabled, use it, otherwise use the old one." The switch's value comes from configuration or a flag service, not from the code.

What it unlocks: you can deploy code with the new feature turned off, and turn it on later without deploying again. You can turn it on for ten percent of users, or one test device, and watch. And if something goes wrong, you turn it off in seconds instead of rolling back a deployment. **Deploying** (code reaches the machines) and **releasing** (users get the behavior) become two separate decisions.

The names: in dot net, Microsoft's feature management library, often paired with Azure App Configuration. Commercial services like LaunchDarkly. Or simply a value in your own configuration.

The catch: every flag is a branch, and old flags pile up into a maze of if-statements no one dares delete. Treat each flag as temporary, with an owner and a removal date.

## Connections

This episode puts names on choices Timothy has already brushed against. His work application uses always-on BackgroundService workers inside a dot net host, started by systemd. That's the first answer to "who starts my code." Now there are six more to compare it with. His microcontroller-to-Pi telemetry path, and any time a device's appearance should start work, is udev territory. Durable execution and reconciliation are both state machines with the bookkeeping done for you: durable execution stores *where you are in a sequence*, and reconciliation stores *where you should be* and keeps steering there. That's a useful pair to set beside the general skills lectures on states and edges.

## Recap

Who starts your code is a design choice. Before writing a loop with a sleep, name the real trigger.

On one Linux machine, systemd timers schedule work with logs, catch-up after downtime, and dependencies. Cron is the older five-field format you'll still see everywhere.

Udev turns hardware events into actions and stable names. Its rules should hand long work to systemd.

Job queues run slow, flaky work in the background, with retries, exponential backoff, and a record of failures. Jobs must be idempotent.

Serverless functions exist only when triggered. They're cheap and need no maintenance, at the cost of cold starts, time limits, and no memory between runs.

Durable execution lets a long, multi-step process survive crashes and wait for days by replaying a history, which is why workflow code must be deterministic.

Reconciliation declares the desired state and loops until reality matches. It's self-healing and idempotent, as long as nobody causes drift by changing things by hand.

Leases make only one machine act at a time, and fencing tokens protect against a machine that wakes up after its lease is gone.

Feature flags separate deploying from releasing.

## Walk questions

One. List as many answers as you can to "who starts my code, and when?" For each one, give a one-sentence smell that would make you choose it.

Two. Explain how durable execution survives a crash using the word "replay", and then explain why reading the current time inside the workflow breaks it.

Three. Your service runs on three machines, and a nightly report must go out exactly once. Walk through a design using a lease, then explain what a fencing token protects against.

# FlightCheck Project Proposal

## Why I am requesting to work individually

I would like to complete this project individually because it combines two areas that are personally meaningful to me: my experience as a student pilot and my interest in computer science. The scope is realistic for one developer, while still giving me the opportunity to demonstrate every stage of full-stack development—from interface design and Flask routing to data modeling, testing, and documentation. Because aviation safety is a subject I already care about, working independently will also let me make informed design decisions and take full responsibility for the final product.

## 1. What do you intend to build?

I intend to build **FlightCheck**, an educational web application that helps student pilots practice preflight risk assessment and route-planning decisions. The app will guide users through the PAVE framework: Pilot, Aircraft, enVironment, and External pressures. After a user enters factors such as fatigue, flight experience, aircraft condition, fuel margin, visibility, wind, and schedule pressure, FlightCheck will generate an explainable risk indicator and a list of factors to mitigate or discuss with an instructor. A route-planning lab will also help users explore wind correction, groundspeed, estimated flight time, fuel requirements, and weather questions.

FlightCheck will not tell a pilot whether a flight is legally safe, and it will not replace official weather or flight-planning sources. Its social value is educational: it encourages student pilots to slow down, recognize when risks are stacking up, and make more deliberate decisions.

## 2. What will you build for the front end?

I will build a responsive HTML/CSS interface with a guided four-step assessment form, one step for each PAVE category. JavaScript will manage the form progress, interactive controls, validation, and mobile-friendly behavior. The results page will show a clear risk indicator, explain which inputs affected the result, and suggest next steps. A route-planning interface will collect airports, checkpoints, aircraft performance, wind, visibility, ceiling, temperature, and fuel information, then present the calculated plan as a readable briefing. A history page will let users review or delete earlier assessments, and an About page will explain the project’s purpose, technology, and safety limitations.

## 3. What will you build for the back end?

I will use Python and Flask for routing, validation, assessment logic, navigation calculations, optional weather retrieval, and database access. The server will validate each submitted field, evaluate the answers with transparent PAVE-based rules, calculate wind correction, groundspeed, time, and estimated fuel, generate tailored feedback, and save completed work. SQLite will store assessment inputs, risk levels, route plans, summaries, and timestamps. The route planner will include a built-in educational assistant, with an optional AI-enhanced explanation when an API key is configured.

## 4. How will you satisfy two point requirements?

- **Persistent data storage:** FlightCheck will use a SQLite database. Completed assessments will remain available after the server is restarted. The database setup and queries will be located in `app.py`.
- **Meaningful POST endpoint:** `POST /assess` will do more than echo form data. It will validate the briefing, run the assessment logic, create tailored findings, insert a new database record, and display the result. A second POST endpoint will delete a selected saved assessment.

If time permits, I will also deploy a public version so that classmates, instructors, and college admissions readers can try the app online.

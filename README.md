# Pux Button - Automating Shipping Process

## Background Story

I was working in a small [firm](https://levus.co), and we had a recurring task that was *time-consuming and tedious*. Every time we received a new order, we had to manually copy the customer's name and address, then send it to our post partner, Herr Pux. Herr Pux would search for a suitable transport company like TNT or UPS to handle the shipping. 

One day, my boss mentioned how great it would be to have a "**Pux Button**" that could automatically track new orders, parse the information, and send an email to our post partner when a new order came in.

Fueled by the idea, I took on the challenge of developing this "Pux Button" as my first serious programming project.

## Development Journey

I started with a simple script that used regex to parse XML output from our PrestaShop webshop's API. Over time, I also realized the importance of using available libraries like xmltodict instead of reinventing the wheel. Parsing XML with regex was an inefficient approach when a library was readily available to make the task easier.

Throughout the development process, I learned a lot about Python, XML, SQL, and working with APIs. I also had the opportunity to practice server configuration on Linux, write deployment bash scripts, and manage cron jobs for scheduling tasks. 

The experience of developing this project for our own needs at the firm allowed me to learn a lot and grow as a programmer.

## Outcomes

### Skill Development
1. **PrestaShop API and XML data handling:** Gained experience working with PrestaShop's API and managing XML data.
2. **Library utilization:** Learned the importance of using existing libraries (like xmltodict) instead of reinventing the wheel (e.g., by using regex for XML parsing).
3. **Python programming:** Improved my Python programming skills by working with various libraries and modules, and enhancing my general programming thinking.
4. **MySQL and Python integration:** Developed a deeper understanding of MySQL queries and their integration with Python.
5. **Email automation:** Enhanced my knowledge of email automation, working with the smtplib library.
6. **Cron jobs and Bash scripting:** Strengthened my understanding of Cron jobs and Bash scripting for automating tasks on the server-side.

### Project Impact

The current version of the project:

- Effectively fetches new orders from the PrestaShop webshop.
- Groups orders based on payment status.
- Sends an automated email with necessary information for paid orders.
- Saves pending orders to a CSV file for future rechecks.
- Rechecks the payment status of pending orders at the beginning of each cycle and adds them to the paid orders list if their status has changed.

Deployed on a server and configured to run on a schedule using a Cron job, this automation has significantly streamlined the order management process for the company and improved overall efficiency.


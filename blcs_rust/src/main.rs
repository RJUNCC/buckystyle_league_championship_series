struct Person {
    name: String,
    age: u32,
    email: String,
}

impl Person {
    fn new(name: String, age: u32, email: String) -> Person {
        Person { name, age, email }
    }

    fn greet(&self) {
        println!("Hi, I'm {}", self.name)
    }

    fn have_birthday(&mut self) {
        self.age += 1;
    }
}

enum Color {
    Red,
    Green,
    Blue,
}

enum Message {
    Text(String),
    Number(i32),
    Location { x: i32, y: i32 },
}

fn main() {
    let mut person = Person {
        name: String::from("Alice"),
        age: 30,
        email: String::from("rojacobe@outlook.com"),
    };

    person.greet();
    person.have_birthday();
    println!("Now {} years old", person.age);
    println!("My email is {}", person.email);

    let jack: Person = Person::new(String::from("Bob"), 25, String::from("jack@example.com"));
    jack.greet();
    jack.age;

    let favorite = Color::Blue;
    match favorite {
        Color::Red => println!("Red like fire"),
        Color::Green => println!("Green like grass"),
        Color::Blue => println!("Blue like sky"),
    }

    let msg = Message::Text(String::from("Hello"));

    match msg {
        Message::Text(content) => println!("Message: {}", content),
        Message::Number(num) => println!("Number: {}", num),
        Message::Location { x, y } => println!("Location: ({}, {})", x, y),
    }

    let mut count = 0;
    loop {
        count += 1;
        if count == 3 {
            break;
        }
        println!("Count: {}", count);
    }

    let mut num = 3;
    while num != 0 {
        println!("{}!", num);
        num -= 1
    }

    for i in 1..=5 {
        println!("{}", i)
    }

    let animals = ["cat", "dog", "bird"];
    for animal in animals.iter() {
        println!("{}", animal);
    }

    let x = 5;
    let mut y = 6;
    y = 6;

    const MAX_POINTS: u32 = 100_000;
    let guess: u32 = "42".parse().expect("Not a number!");

    println!("Guessed: {}", guess)
}

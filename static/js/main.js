// Den här raden skriver till konsollen i webbläsaren. Konsollen syns om man öppnar Developer Tools.
console.log("Hello world!");

// Den här raden använder objektet document, som webbläsaren skapat för att vi ska
// kunna manipulera DOMen. Vi använder document för att hämta en referens till logotypen i sidan och spara den i ev variabel.
var logo = document.getElementById("js-logo");

const form = document.querySelector("form");
const sumButton = document.getElementById("sumButton");
let num1Input = document.getElementById("numInput1");
let operatorInput = document.getElementById("operatorInput");
let num2Input = document.getElementById("numInput2");

let opperations = ["+", "-", "*", "/", "**"];

sumButton.onclick = function (event) {
  let value1 = Number(num1Input.value);
  let value2 = Number(num2Input.value);
  let div = document.getElementById("result");
  let sum = 0;

  if (opperations.includes(operatorInput.value)) {
    console.log("Valid operator");
    sum = `${value1} ${operatorInput.value} ${value2}`;
    sum = eval(sum);
    console.log("Sum is: " + sum);
  } else {
    console.log("Invalid operator, try again");
  }

  // if (operatorInput.value === "+") {
  //   sum = value1 + value2;
  //   console.log("Sum is: " + sum);
  // } else if (operatorInput.value === "-") {
  //   sum = value1 - value2;
  //   console.log("Sum is: " + sum);
  // } else if (operatorInput.value === "*") {
  //   sum = value1 * value2;
  //   console.log("Sum is: " + sum);
  // } else if (operatorInput.value === "/") {
  //   sum = value1 / value2;
  //   console.log("Sum is: " + sum);
  // } else if (operatorInput.value !== opperations) {
  //   console.log("Invalid operator");
  // }

  div.innerHTML = `<div> Sum is: ${sum} </div>`;
};

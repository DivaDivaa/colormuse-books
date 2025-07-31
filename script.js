// Script for ColorMuse Books interactive coloring book generator

// Array to hold generated image paths (demo uses pre-generated samples)
let generatedImages = [];
// Fixed price for a 25-page custom book
const BOOK_PRICE = 29.99;

// Populate preview grid with sample images when user clicks generate
function generatePreview() {
  const prompt = document.getElementById('promptInput').value.trim();
  if (!prompt) {
    alert('Please enter a description of your desired coloring book theme.');
    return;
  }
  // In a real implementation, this would call a backend API that uses AI to
  // generate 25 unique coloring pages based on the prompt. For this demo
  // we rotate through a set of sample images stored in the assets folder.
  generatedImages = [];
  const samples = ['assets/page1.png','assets/page2.png','assets/page3.png'];
  // Push sample images multiple times to mimic 25 pages
  for (let i = 0; i < 25; i++) {
    generatedImages.push(samples[i % samples.length]);
  }
  const previewGrid = document.getElementById('previewGrid');
  previewGrid.innerHTML = '';
  generatedImages.forEach(src => {
    const img = document.createElement('img');
    img.src = src;
    img.alt = 'Coloring page preview';
    previewGrid.appendChild(img);
  });
  // Show the order section with price
  document.getElementById('orderSection').style.display = 'block';
}

// Open the order modal
function openOrderModal() {
  // Show the modal
  document.getElementById('orderModal').style.display = 'flex';
  // Initialize PayPal Buttons the first time the modal opens
  initPayPalButtons();
}

// Close the order modal
function closeOrderModal() {
  document.getElementById('orderModal').style.display = 'none';
}

// Handle order form submission
function submitOrder(event) {
  event.preventDefault();
  const name = document.getElementById('customerName').value.trim();
  const email = document.getElementById('customerEmail').value.trim();
  const address = document.getElementById('customerAddress').value.trim();
  if (!name || !email || !address) {
    alert('Please fill out all fields before submitting your order.');
    return;
  }
  // In a production environment, you would integrate a payment processor
  // (e.g., Stripe) and a print-on-demand API to create and ship the book.
  // For this demo we simply display a confirmation message. In a real
  // implementation, after capturing payment via PayPal, you would send
  // the order details to your backend for processing and printing.
  alert('Thank you, ' + name + '! Your custom coloring book will be processed. We will contact you at ' + email + ' with shipping updates.');
  // Reset form and hide modal
  document.getElementById('orderForm').reset();
  closeOrderModal();
}

// Initialize PayPal buttons for payment
function initPayPalButtons() {
  const container = document.getElementById('paypalContainer');
  // Prevent rendering multiple times if already initialized
  if (!container || container.dataset.rendered === 'true') return;
  // Only proceed if the PayPal SDK has loaded and the paypal object exists
  if (typeof paypal === 'undefined') {
    console.error('PayPal SDK not loaded. Please check the client ID in index.html');
    return;
  }
  paypal.Buttons({
    style: {
      color: 'gold',
      shape: 'rect',
      label: 'pay',
      tagline: false
    },
    createOrder: function(data, actions) {
      // Create an order with the fixed price for the book
      return actions.order.create({
        purchase_units: [{
          amount: {
            value: BOOK_PRICE.toString()
          },
          description: 'Custom AI Coloring Book'
        }]
      });
    },
    onApprove: function(data, actions) {
      // Capture the order after user approves payment
      return actions.order.capture().then(function(details) {
        // Payment successful; hide PayPal container and reveal shipping form
        alert('Payment completed by ' + details.payer.name.given_name + '. Please provide your shipping details.');
        container.style.display = 'none';
        const form = document.getElementById('orderForm');
        if (form) form.style.display = 'block';
      });
    },
    onError: function(err) {
      console.error('PayPal Button Error:', err);
      alert('There was an error processing your payment. Please try again.');
    }
  }).render('#paypalContainer');
  // Mark as rendered to avoid duplicate buttons
  container.dataset.rendered = 'true';
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  // Bind generate button
  const genBtn = document.getElementById('generateBtn');
  if (genBtn) genBtn.addEventListener('click', generatePreview);
  // Bind order button (to open modal)
  const orderBtn = document.getElementById('orderBtn');
  if (orderBtn) orderBtn.addEventListener('click', openOrderModal);
  // Bind cancel button
  const cancelBtn = document.getElementById('cancelOrderBtn');
  if (cancelBtn) cancelBtn.addEventListener('click', closeOrderModal);
  // Bind order form submit
  const form = document.getElementById('orderForm');
  if (form) form.addEventListener('submit', submitOrder);
});
document.addEventListener('DOMContentLoaded', function() {
  // Function to show or hide the reason for uneducation dropdown
  function toggleReasonUneducationDropdown() {
      var education = document.getElementById('education');
      var reasonUneducationContainer = document.getElementById('reason-uneducation-container');

      if (education.value === 'Illiterate') {
          reasonUneducationContainer.style.display = 'block';
      } else {
          reasonUneducationContainer.style.display = 'none';
      }
  }

  // Function to show or hide the reason for unemployment dropdown
  function toggleReasonDropdown() {
      var employedNo = document.getElementById('employed-no');
      var reasonContainer = document.getElementById('reason-container');

      if (employedNo.checked) {
          reasonContainer.style.display = 'block';
      } else {
          reasonContainer.style.display = 'none';
      }
  }

  // Function to show or hide the reason for going abroad dropdown
  function toggleReasonAbroadDropdown() {
      var abroadYes = document.getElementById('abroad-yes');
      var reasonAbroadContainer = document.getElementById('reason-abroad-container');

      if (abroadYes.checked) {
          reasonAbroadContainer.style.display = 'block';
      } else {
          reasonAbroadContainer.style.display = 'none';
      }
  }

  // Add event listeners to the relevant elements
  document.getElementById('education').addEventListener('change', toggleReasonUneducationDropdown);
  document.getElementById('employed-yes').addEventListener('change', toggleReasonDropdown);
  document.getElementById('employed-no').addEventListener('change', toggleReasonDropdown);
  document.getElementById('abroad-yes').addEventListener('change', toggleReasonAbroadDropdown);
  document.getElementById('abroad-no').addEventListener('change', toggleReasonAbroadDropdown);

  // Initial call to set the correct state on page load
  toggleReasonUneducationDropdown();
  toggleReasonDropdown();
  toggleReasonAbroadDropdown();
});

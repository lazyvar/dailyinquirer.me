window.onload = function() {
	let headers = document.querySelectorAll("h3")
	for (header of headers) {
		let innerHtml = header.innerHTML
		header.innerHTML= innerHtml.replace(/\./g, "<span class=\"hack\">.</span>")
	}

	let main = document.getElementsByClassName("main")
	for (row of main) {
		let innerHtml = row.innerHTML
		row.innerHTML = innerHtml.replace(/<br>/g, " ")
	}
}
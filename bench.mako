<table>
  % for row in table:
    <tr>
      % for col in row.values():
        <td>${ col | h  }</td>
      % endfor
    </tr>
  % endfor
</table>
